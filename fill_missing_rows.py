import csv
import json
import fitz  # PyMuPDF
import os
from pathlib import Path
import logging

from core.csv_utils import find_max_csv_field_size
from core.preprocess_text import normalize_spaced_text, clean_text
from core.scale_pdf import scale_pdf
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
                        span["text"] = span["text"].strip()
                        # Skip empty spans
                        if not span["text"]:
                            continue

                        # Normalize text with excessive spacing
                        normalized_text = normalize_spaced_text(span["text"])

                        cell = {
                            "bbox": [
                                span["bbox"][0],
                                span["bbox"][1],
                                span["bbox"][2] - span["bbox"][0],  # width
                                span["bbox"][3] - span["bbox"][1]   # height
                            ],
                            "text": normalized_text,
                            "font": {
                                "color": int_to_rgb(span["color"]),
                                "name": span["font"],
                                "size": int(span["size"]),
                            },
                            "text_vi": normalized_text  # Will be translated later
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
        
    return {"cells": cells}

def get_missing_file_ids(sample_file, submission_file):
    """Identify file IDs with missing or empty solutions"""
    # Get all expected file IDs from sample submission
    expected_ids = set()
    with open(sample_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            if row and row[0]:  # Check if row exists and has an ID
                expected_ids.add(row[0])
    
    # Get IDs with valid solutions from current submission
    existing_solutions = {}
    if os.path.exists(submission_file):
        with open(submission_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            for row in reader:
                if len(row) >= 2:
                    file_id = row[0]
                    solution = row[1]
                    # Store the solution if it's not empty
                    if solution.strip() not in ['[]', '""[]""', '{}', '""{}""']:
                        existing_solutions[file_id] = solution
    
    # Find IDs that don't have valid solutions
    missing_ids = expected_ids - set(existing_solutions.keys())
    
    logging.info(f"Found {len(expected_ids)} expected IDs in sample file")
    logging.info(f"Found {len(existing_solutions)} valid solutions in current submission")
    logging.info(f"Need to process {len(missing_ids)} missing file IDs")
    
    return missing_ids, existing_solutions, expected_ids


def process_missing_files(missing_ids, pdf_dir, existing_solutions, output_file):
    """Process files with missing solutions, apply OCR, and extract text"""
    pdf_dir_path = Path(pdf_dir)
    total_missing = len(missing_ids)
    processed = 0
    success = 0
    
    # Track which file IDs we've already written to prevent duplicates
    written_ids = set()

    # Create/verify output file with header if needed
    if not os.path.exists(output_file):
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["id", "solution"])
    
    # Copy existing valid solutions to new file
    with open(output_file, 'w', newline='', encoding='utf-8') as f:  # Changed from 'a' to 'w' to start fresh
        writer = csv.writer(f)
        writer.writerow(["id", "solution"])  # Write header
        
        for file_id, solution in existing_solutions.items():
            if file_id not in written_ids:  # Prevent duplicates
                writer.writerow([file_id, solution])
                written_ids.add(file_id)
    
    logging.info(f"Copied {len(written_ids)} existing solutions to {output_file}")
    
    # Now append new solutions
    with open(output_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Find and process missing files
        for file_id in sorted(missing_ids):
            if file_id in written_ids:  # Skip if already written
                continue
            
            processed += 1
            logging.info(f"Processing {processed}/{total_missing}: {file_id}")
            
            # Find PDF file in directory
            pdf_file = pdf_dir_path / f"{file_id}.coco_standard.pdf"
            if not pdf_file.exists():
                logging.warning(f"PDF file not found: {pdf_file}")
                continue
            
            try:
                # Apply OCR to the PDF
                ocr_path = apply_ocr_to_pdf(pdf_file)
                if not ocr_path:
                    logging.error(f"OCR failed for {file_id}")
                    continue
                    
                # Extract text and translate it
                result = extract_pdf_info(ocr_path)
                cells = result.get("cells", [])
                
                if not cells:
                    logging.warning(f"No text extracted from OCR'd PDF: {file_id}")
                    continue
                    
                # Save result to CSV
                writer.writerow([file_id, json.dumps(cells, ensure_ascii=False)])
                written_ids.add(file_id)
                
                success += 1
                logging.info(f"Successfully processed {file_id} with {len(cells)} cells")
                
                # Clean up OCR file if it's a temporary file
                # if ocr_path != pdf_file:
                #     try:
                #         os.unlink(ocr_path)
                #     except:
                #         pass
                    
            except Exception as e:
                logging.error(f"Error processing {file_id}: {str(e)}")
    
    return success, total_missing


def main():
    # File paths
    sample_file = "sample_submission.csv"
    current_submission = "submission.csv"
    new_submission = "submission_fill.csv"
    pdf_dir = "data/test/PDF_scaled"  # Directory with original PDF files
    
    # Ensure necessary directories exist
    os.makedirs(pdf_dir, exist_ok=True)
    
    # Get missing file IDs
    missing_ids, existing_solutions, all_expected_ids = get_missing_file_ids(
        sample_file, current_submission)
    
    if not missing_ids:
        logging.info("No missing solutions found. All files have valid solutions!")
        return
    
    # Process missing files
    success, total = process_missing_files(
        missing_ids, pdf_dir, existing_solutions, new_submission)
    
    # Log summary
    logging.info(f"Processing complete!")
    logging.info(f"Successfully processed {success}/{total} missing files")
    logging.info(f"New submission file created: {new_submission}")
    
    # Verify final submission content
    try:
        with open(new_submission, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            final_count = sum(1 for _ in reader)
            
        coverage = (final_count / len(all_expected_ids)) * 100
        logging.info(f"Final submission contains {final_count}/{len(all_expected_ids)} "
                     f"entries ({coverage:.2f}% coverage)")
    except Exception as e:
        logging.error(f"Error verifying final submission: {str(e)}")

if __name__ == "__main__":
    main()