import csv
import json
import fitz  # PyMuPDF
import os
from pathlib import Path
import logging

from core.csv_utils import find_max_csv_field_size
from core.preprocess_text import normalize_spaced_text, clean_text
from core.extract_font_color import int_to_rgb
from core.ocr_img2text import apply_ocr_to_pdf
from core.translate_text import translate_cells


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
    
    # Add translation step
    if cells:
        try:
            logging.info(f"Translating {len(cells)} cells to Vietnamese...")
            cells = translate_cells(cells, target='vi')
            logging.info(f"Translation complete for {len(cells)} cells")
        except Exception as e:
            logging.error(f"Translation error: {str(e)}")
            # Continue with untranslated text

    # Final null check before returning
    for cell in cells:
        if cell.get("text_vi") is None:
            cell["text_vi"] = cell.get("text", "")  # Use original or empty string

    return {"cells": cells}


def get_file_ids(file_path):
    """Get expected file IDs from sample submission file"""
    if not file_path.exists():
        logging.warning(f"Sample submission file not found: {file_path}")
        return set()  # Return empty set if file doesn't exist
        
    expected_ids = set()
    try:
        with open(file_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            for row in reader:
                if row and row[0]:  # Check if row exists and has an ID
                    expected_ids.add(row[0])
        
        logging.info(f"Found {len(expected_ids)} expected file IDs")
        return expected_ids
    except Exception as e:
        logging.error(f"Error reading sample submission: {e}")
        return set()


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
    # File paths
    pdf_dir = Path("data/test/PDF")  # Directory with original PDF files
    ocr_dir = Path("data/test/PDF_ocr")
    output_csv = Path("submission_ocr_official.csv")

    # Ensure necessary directories exist
    os.makedirs(pdf_dir, exist_ok=True)
    os.makedirs(ocr_dir, exist_ok= True)

    # Get all valid file ids from sample_file
    process_all_pdfs(pdf_dir, ocr_dir, output_csv)


if __name__ == "__main__":
    main()