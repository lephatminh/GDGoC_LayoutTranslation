
from pathlib import Path
from core.pdf_utils import convert_pdf_to_imgs
import argparse

def main():
    parser = argparse.ArgumentParser(
        description="Convert a single PDF to images in its own folder."
    )

    parser.add_argument(
        "input_dir", 
        type=Path,
        help="Path to the input PDF (e.g. input/{file_id}/{file_id}.pdf)"
    )

    parser.add_argument(
        "output_dir",
        type=Path,
        help="Directory where the images will be written"
    )

    args = parser.parse_args()

    pdf_path: Path = args.input_dir

    if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
        parser.error(f"{pdf_path} does not exist or is not a .pdf")

    imgs = convert_pdf_to_imgs(
        pdf_path=pdf_path,
        output_folder=pdf_path.parent,
        dpi=300,
        img_format="png"
    )

    for img in imgs:
        print("created:", img)
if __name__ == "__main__":
    main()