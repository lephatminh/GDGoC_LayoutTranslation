import csv
import json
import fitz  # PyMuPDF
import os
from pathlib import Path
import logging

from core.csv_utils import find_max_csv_field_size, load_csv_data_pymupdf, load_csv_data_pdfpig
from core.preprocess_text import normalize_spaced_text, clean_text
from core.extract_math_boxes import load_math_boxes 
from core.ocr_img2text import apply_ocr_to_pdf
from core.translate_text import setup_multiple_models, translate_document
from core.filter_math_related_boxes import filter_text_boxes
from core.visualize_result import visualize_translation_and_math


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("ocr_recovery.log"),
        logging.StreamHandler()
    ]
)


# Safely set maximum CSV field size limit
csv.field_size_limit(find_max_csv_field_size())


def extract_pdf_info(pdf_path):
    """Extract text and formatting information from a PDF file"""
    doc = fitz.open(pdf_path)
    cells = []
    
    try:
        for page_num, page in enumerate(doc, start=1):
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        span["text"] = clean_text(span["text"]).strip()
                        # Skip empty spans
                        if not span["text"]:
                            continue

                        # Normalize text with excessive spacing
                        normalized_text = normalize_spaced_text(span["text"])

                        cell = {
                            "x": span["bbox"][0],
                            "y": span["bbox"][1],
                            "width": span["bbox"][2] - span["bbox"][0],     # width
                            "height": span["bbox"][3] - span["bbox"][1],    # height
                            "text": normalized_text,
                            "text_vi": normalized_text,  # Will be translated later
                            "page": page_num,
                        }
                        cells.append(cell)
    except Exception as e:
        logging.error(f"Error extracting text from {pdf_path}: {str(e)}")
    finally:
        doc.close()

    # Final null check before returning
    for cell in cells:
        if cell.get("text_vi") is None:
            cell["text_vi"] = cell.get("text", "")  # Use original or empty string

    return {"cells": cells}


def process_all_pdfs(pdf_dir, ocr_dir, output_csv):
    # Get all pdf files from pdf_dir
    pdf_files = list(pdf_dir.glob("*.pdf"))
    total_files = len(pdf_files)

    # Create CSV file with header if it doesn't exist
    csv_exists = output_csv.exists()
    if not csv_exists:
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "solution"])
    
    # Keep track of already processed files
    processed_ids = set()
    if csv_exists:
        with open(output_csv, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            # Check if the file has any rows before trying to skip the header
            try:
                next(reader)  # Skip header
                for row in reader:
                    if row:
                        processed_ids.add(row[0])
                print(f"Found {len(processed_ids)} already processed files in submission.csv")
            except StopIteration:
                # File exists but is empty or only contains header
                print("Existing submission.csv appears to be empty. Starting fresh.")
                # Reset the file with just a header
                with open(output_csv, "w", newline="", encoding="utf-8") as f_reset:
                    writer = csv.writer(f_reset)
                    writer.writerow(["id", "solution"])
        print(f"Found {len(processed_ids)} already processed files in submission.csv")

    # Process each PDF and append to CSV immediately
    for idx, pdf_file in enumerate(pdf_files, 1):
        # Extract file ID from filename
        file_id = pdf_file.stem
        
        # Skip if already processed
        if file_id in processed_ids:
            print(f"[{idx}/{total_files}] Skipping already processed: {file_id}")
            continue
            
        print(f"[{idx}/{total_files}] Processing: {pdf_file.name}")
        
        try:
            # Apply OCR to the PDF
            ocr_pdf_file = apply_ocr_to_pdf(pdf_file, ocr_dir)
            if not ocr_pdf_file:
                logging.error(f"OCR failed for {file_id}")
                continue

            # Process PDF and extract cells
            output = extract_pdf_info(ocr_pdf_file)
            cells = output.get("cells", [])
            
            # Append result to CSV immediately
            with open(output_csv, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
                json_str = json.dumps(cells, ensure_ascii=False)
                json_str = clean_text(json_str)
                writer.writerow([file_id, json_str])
                
            processed_ids.add(file_id)
            print(f"Saved result for {file_id} to {output_csv}")
            
        except Exception as e:
            print(f"Error processing {file_id}: {str(e)}")
            continue

    print(f"Processing complete! {len(processed_ids)} files processed.")


def main():
    current_dir = Path(__file__).parent
    # File paths
    pdf_dir = Path("data/test/testing")  # Directory with original PDF files
    ocr_dir = Path("data/test/PDF_ocr")
    output_csv = Path("submission_ocr_official.csv")
    pdfpig_csv = Path("submission_pdfpig.csv")  # PDFPig output for context extraction
    math_notation_dir = Path("YOLO_Math_detection")  # Directory with math notation detection results
    visualization_dir = Path("visualized_translations")
    font_file_path = Path("Roboto.ttf")  # Path to font file for visualization
    translated_json_path = current_dir / "translated.json"

    # Ensure necessary directories exist
    os.makedirs(pdf_dir, exist_ok=True)
    os.makedirs(ocr_dir, exist_ok= True)
    os.makedirs(visualization_dir, exist_ok=True)

    # Create API manager and setup models
    api_manager = setup_multiple_models()

    # Process all PDFs and generate CSV
    process_all_pdfs(pdf_dir, ocr_dir, output_csv)

    # Load PyMuPDF boxes
    pdf_boxes = load_csv_data_pymupdf(current_dir / "submission_ocr_official.csv")

    # Load paragraph context data from PDFPig if available
    context_boxes = {}
    if pdfpig_csv.exists():
        print("Loading PDFPig data for context extraction...")
        context_boxes = load_csv_data_pdfpig(pdfpig_csv)
        print(f"Loaded context data for {len(context_boxes)} files")
    else:
        # execute PDFPigLayoutDetection/Program.cs then load paragraph context data 
        pass

    # Load existing translations if the file exists
    if translated_json_path.exists():
        with open(translated_json_path, "r", encoding="utf-8") as f:
            all_translations = json.load(f)
        print(f"Loaded {len(all_translations)} translated files from translated.json")
    else:
        all_translations = {}

    # Loop through all files
    # all_translations = {}
    for file_id, boxes in pdf_boxes.items():
        print(f"Processing file: {file_id}")

        # Detect Math Equation boxes for each file
        math_boxes = [] 
        try:
            math_boxes = load_math_boxes(math_notation_dir, file_id)
        except Exception as e:
            print(f"  Error detecting math boxes: {e}")
        
        # Remove boxes in pymupddf overlapped with Math Equation boxes from source_text
        filtered_boxes = boxes.copy()
        if math_boxes:
            try:
                filtered_boxes = filter_text_boxes(boxes, math_boxes)
                print(f"  Kept {len(filtered_boxes)} of {len(boxes)} text boxes after math filtering")
            except Exception as e:
                print(f"  Error filtering math boxes: {e}")
            
        # Translate text into text_vi
        if file_id in all_translations:
            print(f"  Already translated {file_id}, skipping translation")
            translated_boxes = all_translations[file_id]
        else:
            translated_boxes = translate_document(filtered_boxes, api_manager, context_boxes[file_id])
        
        # text_vi insertion into original pdf
        # math equation image insertion into original pdf 
        all_translations[file_id] = translated_boxes

        try:
            # Find the original PDF
            pdf_path = ocr_dir / f"{file_id}.ocr.pdf"
            
            if pdf_path:
                output_pdf = visualization_dir / f"{file_id}_translated.pdf"
                visualize_translation_and_math(pdf_path, translated_boxes, math_boxes, output_pdf,
                                      font_file_path, math_notation_dir / file_id)
                print(f"  Created visualization at {output_pdf}")
            else:
                print(f"  Could not find PDF for {file_id}, skipping visualization")
        except Exception as e:
            print(f"  Error creating visualization: {e}")

    with open("translated.json", "w", encoding="utf-8") as outfile:
        json.dump(all_translations, outfile, indent=4, ensure_ascii=False)
        print(f"Saved all translations to translated.json")
    # Visualize the translations

if __name__ == "__main__":
    main()