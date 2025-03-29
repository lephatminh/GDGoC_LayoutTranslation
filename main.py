import fitz  # PyMuPDF
import json
import csv
import os
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter, Transformation
import copy

def int_to_rgb(color_int):
    """Convert integer color to RGB tuple."""
    if color_int < 0:
        color_int = color_int & 0xFFFFFFFF

    a = (color_int >> 24) & 0xFF
    r = (color_int >> 16) & 0xFF
    g = (color_int >> 8) & 0xFF
    b = color_int & 0xFF

    if (a == 0):
        a = 255

    return [r, g, b, a]

def extract_pdf_info(pdf_path, output_json_path=None):
    doc = fitz.open(pdf_path)
    output = {}
    
    # Extract text cells
    cells = []
    for page_num, page in enumerate(doc, start=1):
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    cell = {
                        "bbox": [
                            span["bbox"][0], 
                            span["bbox"][1],
                            span["bbox"][2] - span["bbox"][0],  # width
                            span["bbox"][3] - span["bbox"][1]   # height
                        ],
                        "text": span["text"].strip(),
                        "font": {
                            "color": int_to_rgb(span["color"]),
                            "name": span["font"],
                            "size": 1  # Normalized size
                        },
                        "text_vi": span["text"].strip()  # Placeholder for Vietnamese translation
                    }

                    if (cell["text"]): 
                        cells.append(cell)

    output["cells"] = cells

    if output_json_path:
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

    return output

def scale_pdf_properly(input_path, output_path, target_width=1025, target_height=1025):
    """
    Scale a PDF to the target dimensions ensuring both page size and content are scaled.

    Args:
        input_path (str): Path to the input PDF file
        output_path (str): Path where the scaled PDF will be saved
        target_width (int): Target width in pixels (default: 1025)
        target_height (int): Target height in pixels (default: 1025)
    """
    # Read the original PDF
    reader = PdfReader(input_path)
    writer = PdfWriter()

    # Convert target dimensions from pixels to points (72 points = 1 inch)
    # Assuming 72 DPI resolution
    target_width_pts = target_width
    target_height_pts = target_height

    # Process each page
    for page_num in range(len(reader.pages)):
        # Get the original page
        original_page = reader.pages[page_num]

        # Get original page dimensions
        mediabox = original_page.mediabox
        orig_width = float(mediabox.width)
        orig_height = float(mediabox.height)

        # Calculate scaling factors
        width_scale = target_width_pts / orig_width
        height_scale = target_height_pts / orig_height

        # Create a copy of the page to work with
        page = copy.deepcopy(original_page)

        # Apply scaling transformation to the content
        transform = Transformation().scale(width_scale, height_scale)
        page.add_transformation(transform)

        # Update the mediabox to the new dimensions
        # PyPDF2 uses a coordinate system with (0,0) at the bottom left
        page.mediabox.lower_left = (0, 0)
        page.mediabox.upper_right = (target_width_pts, target_height_pts)

        # Also update cropbox and trimbox if they exist
        if "/CropBox" in page:
            page.cropbox.lower_left = (0, 0)
            page.cropbox.upper_right = (target_width_pts, target_height_pts)

        if "/TrimBox" in page:
            page.trimbox.lower_left = (0, 0)
            page.trimbox.upper_right = (target_width_pts, target_height_pts)

        if "/ArtBox" in page:
            page.artbox.lower_left = (0, 0)
            page.artbox.upper_right = (target_width_pts, target_height_pts)

        if "/BleedBox" in page:
            page.bleedbox.lower_left = (0, 0)
            page.bleedbox.upper_right = (target_width_pts, target_height_pts)

        # Add the scaled page to the output PDF
        writer.add_page(page)

    # Write the result to the output file
    with open(output_path, "wb") as output_file:
        writer.write(output_file)

    print(f"PDF scaled successfully to {target_width}x{target_height}.")
    print(f"Both page dimensions and content have been scaled. Saved to {output_path}")

def process_all_pdfs():
    pdf_dir = Path("data/test/PDF")
    output_csv = Path("submission.csv")

    pdf_files = list(pdf_dir.glob("*.pdf"))
    total_files = len(pdf_files)

    # Scale all PDFs to COCO standard size
    scaled_dir = Path("data/test/PDF_scaled")
    os.makedirs(scaled_dir, exist_ok=True)

    scaled_pdf_files = list(scaled_dir.glob("*.pdf"))
    total_scaled_files = len(scaled_pdf_files)

    scaled_pdf_paths = []
    # Check if all PDFs have already been scaled
    if total_scaled_files == total_files:
        print("All PDFs have already been scaled.")
        for pdf_file in pdf_files:  
            output_pdf_path = scaled_dir / f"{pdf_file.stem}.coco_standard.pdf"
            scaled_pdf_paths.append(output_pdf_path)
    
    else:
        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"[{i}/{total_files}] Scaling: {pdf_file.name}")
            output_pdf_path = scaled_dir / f"{pdf_file.stem}.coco_standard.pdf"
            scale_pdf_properly(pdf_file, output_pdf_path)
            scaled_pdf_paths.append(output_pdf_path)

    results = {}
    # During first iteration, i will be 1
    for idx, scaled_pdf_file in enumerate(scaled_pdf_paths, 1):
        print(f"Processing {idx + 1}/{total_files}: {scaled_pdf_file.name}")
        file_id = scaled_pdf_file.stem  # Use filename without extension as ID
        cells = extract_pdf_info(scaled_pdf_file)
        # Remove the "cells" key from the dictionary
        cells = cells.get("cells", [])
        results[file_id] = cells

    # No extra newlines are inserted between rows in the CSV file
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "solution"])

        for file_id, cells in results.items():
            # remove suffix "with_coco_standard"
            file_id = file_id.replace(".coco_standard", "")
            solution = json.dumps(cells)
            writer.writerow([file_id, solution])

    print(f"Complete! Processed {len(results)} PDF files.")

if __name__ == "__main__":
    process_all_pdfs()