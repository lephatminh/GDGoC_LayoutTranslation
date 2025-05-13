import csv
import json
import fitz  # PyMuPDF
from typing import List, Dict 
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

    return {"cells": cells}


def process_single_pdf(
    file_id: str,
    pdf_path: Path,
    ocr_dir: Path,
    translation_cache: Dict[str, List],
    context_boxes: Dict[str, List],
    api_manager,
    math_dir: Path,
    viz_dir: Path,
    font_path: Path,
) -> List[Dict]:
    # OCR pdf for no selectable texts
    ocr_pdf = apply_ocr_to_pdf(pdf_path, ocr_dir)
    if not ocr_pdf:
        logging.error(f"OCR failed for {file_id}")
        return []
    
    # Extract pdf vital info
    cells = extract_pdf_info(ocr_pdf)

    # Remove math overlaps
    math_boxes = load_math_boxes(math_dir, file_id) or []
    if math_boxes:
        cells = filter_text_boxes(cells, math_boxes)
        logging.info(f"{file_id}: {len(cells)} cells after math filtering")

    # Translate
    if file_id in translation_cache:
        translated = translation_cache[file_id]
        logging.info(f"{file_id}: using cached translation")
    else:
        translated = translate_document(cells, api_manager, context_boxes.get(file_id, []))
        translation_cache[file_id] = translated

    # Visualize
    output_pdf = viz_dir / f"{file_id}_translated.pdf"
    visualize_translation_and_math(
        ocr_pdf, translated, math_boxes, output_pdf, font_path, math_dir / file_id
    )
    logging.info(f"{file_id}: visualization saved to {output_pdf}")

    return translated


def main():
    root = Path(__file__).parent
    pdf_dir = root / "data" / "test" / "PDF"
    ocr_dir = root / "data" / "test" / "PDF_ocr"
    viz_dir = root / "visualized_translations"
    output_csv = root / "submission_ocr_official.csv"
    pdfpig_csv = root / "submission_pdfpig.csv"
    math_dir = root / "YOLO_Math_detection"
    font_path = root / "Roboto.ttf"
    translated_json = root / "translated.json"

    # Ensure necessary directories exist
    for d in (pdf_dir, ocr_dir, viz_dir):
        d.mkdir(parents=True, exist_ok=True)


    # Create API manager and setup models
    api_manager = setup_multiple_models()

    # Load contexts and caches
    context_boxes = load_csv_data_pdfpig(pdfpig_csv) if pdfpig_csv.exists() else {}
    translation_cache = {}
    if translated_json.exists():
        translation_cache = json.loads(translated_json.read_text(encoding="utf-8"))
        logging.info(f"Loaded {len(translation_cache)} cached translations")

    # Load processed files
    processed = set()
    if output_csv.exists():
        reader = csv.reader(output_csv.open("r", encoding="utf-8"))
        next(reader, None)
        processed = {row[0] for row in reader if row}

    writer = csv.writer(output_csv.open("a", newline="", encoding="utf-8"))
    if not processed:
        writer.writerow(["id", "solution"])

    # Main loop
    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    for idx, pdf_path in enumerate(pdf_files, start = 1):
        file_id = pdf_path.stem
        if file_id in processed:
            logging.info(f"[{idx}/{len(pdf_files)}] Skipping {file_id}")
            continue

        logging.info(f"[{idx}/{len(pdf_files)}] Processing {file_id}")

        translated_cells = process_single_pdf(
            file_id,
            pdf_path,
            ocr_dir,
            translation_cache,
            context_boxes,
            api_manager,
            math_dir,
            viz_dir,
            font_path
        )

        # append to CSV
        writer.writerow([file_id, json.dumps(translated_cells, ensure_ascii=False)])
        processed.add(file_id)    

    # Save cache
    translated_json.write_text(json.dumps(translation_cache, ensure_ascii=False, indent=2), encoding="utf-8")
    logging.info("All done.")


if __name__ == "__main__":
    main()