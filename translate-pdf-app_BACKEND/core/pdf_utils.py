import fitz
import os
from PIL import Image
from pathlib import Path
from typing import List

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

    # Convert each page to an image
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)

        # Create a matrix for rendering at higher resolution
        mat = fitz.Matrix(zoom, zoom)

        # Render the page to a pixmap (image)
        pix = page.get_pixmap(matrix=mat)

        # Convert pixmap to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Generate output filename
        output_file = os.path.join(
            output_folder,
            f"{os.path.splitext(os.path.basename(pdf_path))[0]}_page_{page_num + 1}.{img_format}"
        )

        # Save the image
        img.save(output_file)
        output_files.append(output_file)

        print(f"Converted page {page_num + 1}/{len(pdf_document)}")

    pdf_document.close()

    return output_files