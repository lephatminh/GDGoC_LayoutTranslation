from pathlib import Path
from core.pdf_utils import *
from core.detect_layout       import detect_and_crop_image, get_model as _get_layout_model
from core.translate_text      import translate_single_box, setup_multiple_models as _setup_multiple_models
from core.extract_info         import extract_content_from_single_image, get_content_in_region
from core.render_latex         import add_selectable_latex_to_pdf
from core.pymupdf_draw_bb      import draw_boxes_on_pdf
from core.remove_overlapped     import remove_overlapped_boxes
from core.insert_table_text     import insert_translated_table_text
from dataclasses               import asdict
from core.box                  import BoxLabel, Box
import json, argparse, time, logging
from functools                  import lru_cache
from concurrent.futures        import ThreadPoolExecutor, as_completed
import fitz  # PyMuPDF
logger = logging.getLogger(__name__)

#––– Lazy singletons –––
@lru_cache(maxsize=1)
def get_api_manager():
    logger.info("Initializing Gemini ApiKeyManager…")
    start = time.time()
    mgr = _setup_multiple_models()
    logger.info(f"Gemini warmed up in {time.time()-start:.1f}s")
    return mgr

@lru_cache(maxsize=1)
def get_layout_model():
    logger.info("Downloading & loading DocLayout model…")
    start = time.time()
    mdl = _get_layout_model()
    logger.info(f"DocLayout model ready in {time.time()-start:.1f}s")
    return mdl

# first‐touch the models here (once per process)
api_manager    = get_api_manager()
doclayout_model= get_layout_model()
font_path      = Path(__file__).parent / "font" / "Roboto.ttf"

def run_pipeline(pdf_path: Path, output_root: Path):
    imgs = convert_pdf_to_imgs(
        pdf_path=pdf_path,
        output_folder=pdf_path.parent,
        dpi=300,
        img_format="png"
    )

    imgs: list[Path] = [Path(p) for p in imgs]

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
        raw_boxes = detect_and_crop_image(
            image_path=img,
            output_dir=para_cropped_dir,
            page_num=page_num,
            model=doclayout_model
        )

        # Remove overlapped boxes
        raw_boxes = remove_overlapped_boxes(raw_boxes)

        # Separate para_boxes, table_boxes via box.label
        # table_boxes = [b for b in raw_boxes if b.label == BoxLabel.TABLE]
        # para_boxes  = [b for b in raw_boxes if b.label != BoxLabel.TABLE]

        # visual_pdf = output_dir / f"{file_id}_tables.pdf"
        # draw_boxes_on_pdf(
        #     pdf_path=pdf_path,
        #     boxes=table_boxes,
        #     output_path=visual_pdf,
        # )

        # Extract content from table boxes
        doc = fitz.open(str(pdf_path))
        pdf_size = (doc[0].rect.width, doc[0].rect.height)
        dpi = 300
        page = doc[page_num]
        pdf_size = (page.rect.width, page.rect.height)
        # render at your dpi to get back the image size you used for detection
        pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
        image_size = (pix.width, pix.height)

        # # scale the table‐box coords from image→PDF
        # for box in table_boxes:
        #     box.coords = scale_img_box_to_pdf_box(
        #         box.coords,      
        #         image_size,      
        #         pdf_size         
        #     )

        # table_content =  get_content_in_region(doc, table_boxes)

        # # Extract content from the cropped images
        # pdf_content = extract_content_from_multiple_images(para_boxes, para_cropped_dir, api_manager)

        # # Append table content to pdf_content
        # pdf_content.extend(table_content)
        # translated_boxes = translate_document(pdf_content, api_manager)
        translated_boxes: list[Box] = []
        with ThreadPoolExecutor(max_workers=8) as executor:
        # kick off extraction for each cropped box
            extract_futs = {
                executor.submit(extract_content_from_single_image, box, para_cropped_dir, api_manager): box
                for box in raw_boxes
            }

            # as soon as one extraction is done, hand it off to translation
            translate_futs = []
            for ext_fut in as_completed(extract_futs):
                box_with_content = ext_fut.result()
                translate_futs.append(
                    executor.submit(translate_single_box, box_with_content, api_manager)
                )

            # collect translations
            for tx_fut in as_completed(translate_futs):
                translated_boxes.append(tx_fut.result())
            # Translate the content
        

        # Dump the translated boxes to a JSON file
        with open(output_dir/f"{file_id}_translated_boxes.json", "w", encoding= "utf-8") as f:
            json.dump([asdict(box) for box in translated_boxes], f, indent=4, ensure_ascii=False)

        for box in translated_boxes:
            if box.label == BoxLabel.TABLE:
                insert_translated_table_text(doc, box, font_path)
                continue
            box.coords = scale_img_box_to_pdf_box(box.coords, image_size, pdf_size)
            add_selectable_latex_to_pdf(pdf_path, output_dir/f"{file_id}.pdf", box.translation, 
                                        box, doc,box.page_num, 
                                        get_font_size(box.coords, doc[box.page_num]))

        doc.save(output_dir/f"{file_id}.pdf")
        doc.close()
        
def main():
    parser = argparse.ArgumentParser(description="Translate PDF using Gemini API")
    parser.add_argument("pdf_path", type=str, help="Path to the input PDF file")
    parser.add_argument("output_root", type=str, help="Path to the output directory")
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path)
    output_root = Path(args.output_root)

    run_pipeline(pdf_path, output_root)

if __name__ == "__main__":
    main()