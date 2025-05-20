
from pathlib import Path
from core.pdf_utils import *
from core.detect_layout import detect_and_crop_image, get_model
from core.translate_text import translate_document
from core.extract_info import *
from core.render_latex import *
from dataclasses import asdict
import json
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
    output_root: Path = args.output_dir

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
        page_num = int(img_name.split("_")[-1])

        # Create a subfolder for each image
        output_dir = output_root / file_id
        output_dir.mkdir(parents=True, exist_ok=True)

        para_cropped_dir = output_dir / "para_cropped"
        para_cropped_dir.mkdir(parents=True, exist_ok=True)

        # Detect and crop the image
        para_boxes = detect_and_crop_image(
            image_path=img,
            output_dir=para_cropped_dir,
            page_num=page_num,
            model=doclayout_model
        )

        pdf_content = extract_content_from_multiple_images(para_boxes, para_cropped_dir, api_manager)

        # Translate the content
        translated_boxes = translate_document(pdf_content, api_manager)

            
        doc = fitz.open(str(pdf_path))
        pdf_size = (doc[0].rect.width, doc[0].rect.height)
        dpi = 300
        # Dump the translated boxes to a JSON file
        with open(output_dir/f"{file_id}_translated_boxes.json", "w", encoding= "utf-8") as f:
            json.dump([asdict(box) for box in translated_boxes], f, indent=4, ensure_ascii=False)
        for box in translated_boxes:
            page = doc[box.page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
            image_size = (pix.width, pix.height)
            box.coords = scale_img_box_to_pdf_box(box.coords, image_size, pdf_size)
            add_selectable_latex_to_pdf(pdf_path, output_dir/f"{file_id}.pdf", box.translation, box.coords[0],
                                        box.coords[1], box.coords[2], box.coords[3], doc,box.page_num, 
                                        get_font_size(box.coords, doc[box.page_num]))

        doc.close()
        
if __name__ == "__main__":
    main()