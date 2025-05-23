from PIL import Image
from pathlib import Path
from typing import List
from core.box import Box
import fitz
import os

def split_pdf_to_pages(input_pdf_path: Path, output_root: Path) -> None:
    file_id = input_pdf_path.stem
    target_dir = output_root / file_id
    target_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(input_pdf_path))
    for i in range(doc.page_count):
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=i, to_page=i)
        out_pdf = target_dir / f"{file_id}_page_{i+1}.pdf"
        new_doc.save(str(out_pdf))
        new_doc.close()
    doc.close()

def convert_pdf_to_imgs(pdf_path: Path, output_folder: Path, dpi: int = 300, img_format: str = "png") -> List[Path]:
    """
    Convert a PDF file to images.

    Args:
        pdf_path (str): Path to the PDF file
        output_folder (str): Folder to save the images
        dpi (int): DPI for the output images (higher means better quality but larger files)
        image_format (str): Format to save the images (png, jpg, etc.)

    Returns:
        list: List of paths to the generated images
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Open the PDF
    pdf_document = fitz.open(pdf_path)

    output_files = []

    # Calculate the zoom factor based on DPI (72 is the base DPI)
    zoom = dpi / 72

    # Capture the original PDF size
    # pdf_size = (pdf_document[0].rect.width, pdf_document[0].rect.height)

    # Convert each page to an image
    # pil_sizes = []
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)

        # Create a matrix for rendering at higher resolution
        mat = fitz.Matrix(zoom, zoom)

        # Render the page to a pixmap (image)
        pix = page.get_pixmap(matrix=mat)

        # Convert pixmap to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Get the size of the image
        # img_size = (pix.width, pix.height)
        # pil_sizes.append(img_size)

        # Generate output filename
        output_file = os.path.join(
            output_folder,
            f"{os.path.splitext(os.path.basename(pdf_path))[0]}_page_{page_num}.{img_format}"
        )

        # Save the image
        img.save(output_file)
        output_files.append(output_file)

        print(f"Converted page {page_num + 1}/{len(pdf_document)}")

    pdf_document.close()

    return output_files

def get_avg_font_size_overlapped(coords: List[float], page: fitz.Page) -> float:
    """
    Get the average font size of all text spans overlapping the given box.
    """
    x0, y0, x1, y1 = coords
    text_json = page.get_text("dict")
    sizes: List[float] = []

    for block in text_json["blocks"]:
        if block.get("type") != 0:  # only text blocks
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                sx0, sy0, sx1, sy1 = span["bbox"]
                # simple overlap test
                if not (sx1 < x0 or sx0 > x1 or sy1 < y0 or sy0 > y1):
                    sizes.append(span["size"])

    if not sizes:
        return 9.0
    return min(sum(sizes) / len(sizes), 14)

def get_avg_font_size_by_boxes(boxes: List[Box], page: fitz.Page) -> float:
    """
    Get the average font size of all text spans overlapping the given box.
    """
    sizes: List[float] = []
    for box in boxes:
        x0, y0, x1, y1 = box.coords
        text_json = page.get_text("dict")
        for block in text_json["blocks"]:
            if block.get("type") != 0:  # only text blocks
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    sx0, sy0, sx1, sy1 = span["bbox"]
                    sizes.append(span["size"])

    return min(sum(sizes) / max(len(sizes), 1), 14.0)

def scale_img_box_to_pdf_box(image_box, image_size, pdf_size):
    x1, y1, x2, y2 = image_box
    image_width, image_height = image_size
    pdf_width, pdf_height = pdf_size

    scale_x = pdf_width / image_width
    scale_y = pdf_height / image_height

    scaled_x1 = x1 * scale_x
    scaled_y1 = y1 * scale_y
    scaled_x2 = x2 * scale_x
    scaled_y2 = y2 * scale_y

    return [scaled_x1, scaled_y1, scaled_x2, scaled_y2]
