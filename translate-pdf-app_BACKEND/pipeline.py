
from pathlib import Path
from core.pdf_utils import convert_pdf_to_imgs
from core.detect_layout import detect_and_crop_image, get_model
from core.translate_text import *
from core.extract_info import *
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
        help="Path to the output directory (e.g. output/{file_id})"
    )

    args = parser.parse_args()

    pdf_path: Path = args.input_dir
    out_root: Path = args.output_dir

    if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
        parser.error(f"{pdf_path} does not exist or is not a .pdf")

    imgs = convert_pdf_to_imgs(
        pdf_path=pdf_path,
        output_folder=pdf_path.parent,
        dpi=300,
        img_format="png"
    )

    imgs: list[Path] = [Path(p) for p in imgs]

    # Set up
    api_manager = setup_multiple_models()
    doclayout_model = get_model()

    # Detect layout for each image in pdf_path.parent
    for img in imgs:
        img_name = img.stem
        file_id = img_name.split("_")[0]
        # page_num = int(img_name.split("_")[-1])
        page_num = int(img_name.rsplit("_", 1)[1])

        # Create a subfolder for each image
        img_output_dir = out_root / file_id
        img_output_dir.mkdir(parents=True, exist_ok=True)

        para_cropped_dir = img_output_dir / "para_cropped"
        para_cropped_dir.mkdir(parents=True, exist_ok=True)

        # Detect and crop the image
        para_boxes = detect_and_crop_image(
            image_path=img,
            output_dir=para_cropped_dir,
            page_num=page_num,
            model=doclayout_model
        )

        pdf_content = extract_content_from_multiple_images(para_boxes, para_cropped_dir, api_manager)
        
if __name__ == "__main__":
    main()