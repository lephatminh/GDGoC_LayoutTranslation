import argparse
import csv
import json
import fitz  # PyMuPDF
import logging
import os
from pathlib import Path
from typing import List, Dict

from core.csv_utils import find_max_csv_field_size, load_csv_data_pymupdf, load_csv_data_pdfpig
from core.preprocess_text import normalize_spaced_text, clean_text
from core.ocr_img_to_text import apply_ocr_to_pdf
from core.translate_text import setup_multiple_models, translate_document
from core.filter_math_related_boxes import filter_text_boxes
from core.visualize_result import visualize_translation_and_math
from core.detect_math_images import detect_math_box_images
from core.reconstruct_text_math_boxes import (
    insert_cell_id,
    load_math_boxes as load_reconstruct_math_boxes,
    reconstruct_text_cell,
    cut_cells_box,
)
from ultralytics import YOLO

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("ocr_recovery.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("pipeline")

# Increase CSV field size for deep JSON blobs
csv.field_size_limit(find_max_csv_field_size())


def extract_pdf_info(pdf_path: Path) -> Dict:
    """Extract text & formatting info from a PDF file via PyMuPDF."""
    doc = fitz.open(pdf_path)
    cells = []
    try:
        for page_num, page in enumerate(doc, start=1):
            for block in page.get_text("dict")["blocks"]:
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
        logger.error(f"Error extracting text from {pdf_path}: {str(e)}")
    finally:
        doc.close()

    return { "cells": cells }


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
    yolo_weights: Path,
) -> List[Dict]:
    # OCR pdf for no selectable texts
    ocr_pdf = apply_ocr_to_pdf(pdf_path, ocr_dir)
    if not ocr_pdf:
        logger.error(f"OCR failed for {file_id}")
        return []
    
    # Extract pdf vital info
    info = extract_pdf_info(ocr_pdf)
    cells = info.get("cells", [])

    # --- Detect math images ---
    # (1) Prepare per-file math folder
    math_folder = math_dir / file_id
    math_folder.mkdir(parents=True, exist_ok=True)

    # (2) Load YOLO once per file and run full pipeline
    model = YOLO(str(yolo_weights))
    detect_math_box_images(str(pdf_path), str(math_folder), model)
    logger.info(f"math_folder: {math_folder}")

    # --- Reconstruct math vs text cells around detected regions ---
    # 1) assign unique IDs to each extracted text‐cell
    cells = insert_cell_id(cells)

    # 2) load the scaled PDF coords you just generated (if any)
    pdf_coor = math_folder / "pdf_coor.txt"
    if pdf_coor.exists() and pdf_coor.stat().st_size > 0:
        math_list = load_reconstruct_math_boxes(str(pdf_coor)) or []
        # 3) split into merged math boxes vs cells to cut vs cells to keep
        merged_boxes, overlap_ids, cut_list, remain_ids = reconstruct_text_cell(cells, math_list)
        # 4) re-OCR the cut cells
        reocr_cells = cut_cells_box(str(ocr_pdf), cut_list, remain_ids)
        # 5) collect the untouched cells
        remain_cells = [c for c in cells if c["id"] in remain_ids]
        # 6) final text-cells + math_boxes for viz
        cells = reocr_cells + remain_cells
        math_boxes = merged_boxes
        logger.info(f"{file_id}: reconstructed → {len(cells)} text cells, {len(math_boxes)} math boxes")
    else:
        # no math found → skip reconstruct, keep all cells
        math_boxes = []
        logger.info(f"{file_id}: no math coords at {pdf_coor}, skipping reconstruct (keeping {len(cells)} cells)")

    # Translate
    if file_id in translation_cache:
        translated = translation_cache[file_id]
        logger.info(f"{file_id}: using cached translation")
    else:
        translated = translate_document(cells, api_manager, context_boxes.get(file_id, []))
        translation_cache[file_id] = translated

    # Visualize
    output_pdf = viz_dir / f"{file_id}_translated.pdf"
    visualize_translation_and_math(
        ocr_pdf, translated, math_boxes, output_pdf, font_path, math_dir / file_id
    )
    logger.info(f"{file_id}: visualization saved to {output_pdf}")

    return translated


def main():
    for dir in["input", "output"]:
        os.makedirs(dir, exist_ok=True)

    parser = argparse.ArgumentParser(
        description="Run OCR→layout→translate→viz pipeline, optionally per‐file."
    )
    parser.add_argument("--input",  type=Path, help="Path to a single PDF to process")
    parser.add_argument("--output", type=Path, help="Output directory for single‐file mode")
    args = parser.parse_args()

    root = Path(__file__).parent

    # 1) decide batch vs single‐file mode
    if args.input and args.output:
        pdf_paths = [args.input]
        out_root = args.output
        out_root.mkdir(parents=True, exist_ok=True)
    else:
        pdf_paths = sorted((root / "input").glob("*.pdf"))
        out_root = root / "output"
        out_root.mkdir(parents=True, exist_ok=True)

    # 2) load contexts from PDFPig
    context_csv = root / "PDFPigLayoutDetection" / "submission_contexts.csv"
    context_boxes = load_csv_data_pdfpig(context_csv) if context_csv.exists() else {}

    # 3) setup translation API
    api_manager = setup_multiple_models()
    translation_cache: Dict[str, List] = {}
    cached_file = out_root / "translation_cache.json"
    if cached_file.exists() and cached_file.stat().st_size > 0:
        translation_cache = json.loads(cached_file.read_text(encoding="utf-8"))
        logger.info(f"Loaded {len(translation_cache)} cached translations")

    # 4) loop & process
    for pdf_path in pdf_paths:
        file_id = pdf_path.stem
        logger.info(f"Processing {file_id}")

        translated = process_single_pdf(
            file_id,
            pdf_path,
            out_root / file_id,        # ocr_dir
            translation_cache,
            context_boxes,
            api_manager,
            out_root,                  # math_dir
            out_root / file_id,        # viz_dir
            root / "font" / "Roboto.ttf",
            root / "config" / "best.pt",
        )

        # save per‐file CSV if you want (optional)
        # with open(out_root/f"{file_id}.csv", "w", newline="") as f:
        #     writer = csv.writer(f)
        #     writer.writerow(["id","solution"])
        #     writer.writerow([file_id, json.dumps(translated, ensure_ascii=False)])

    # 5) done
    cached_file.write_text(json.dumps(translation_cache, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Pipeline completed.")


if __name__ == "__main__":
    main()