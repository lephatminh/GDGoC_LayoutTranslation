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
from threading import Lock
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
font_path      = Path(__file__).parent / "font" / "NotoSerif-Regular.ttf"

def run_pipeline(pdf_path: Path, output_root: Path): 
    # Create file_id from the PDF name 
    file_id = pdf_path.stem 
     
    # Create output directory structure 
    output_dir = output_root / file_id 
    output_dir.mkdir(parents=True, exist_ok=True) 
     
    # Create specific output PDF path 
    output_pdf = output_dir / f"{file_id}.pdf" 
     
    # 0) open input PDF once 
    doc = fitz.open(str(pdf_path)) 
 
    # will hold all boxes (across all pages) 
    all_boxes: List[Box] = [] 
 
    # 1) for each page, detect & crop 
    imgs = convert_pdf_to_imgs(pdf_path=pdf_path, 
                               output_folder=pdf_path.parent, 
                               dpi=300, img_format="png") 
    
    doc = fitz.open(str(pdf_path)) 
    for img_path in imgs: 
        img = Path(img_path) 
        page_num = int(img.stem.split("_")[-1]) 
 
        # Create per-page crop folder within output directory 
        para_cropped_dir = output_dir / "para_cropped" / f"page_{page_num}" 
        para_cropped_dir.mkdir(parents=True, exist_ok=True) 
 
        # detect & crop 
        boxes = detect_and_crop_image( 
            image_path=img, 
            output_dir=para_cropped_dir, 
            page_num=page_num, 
            model=doclayout_model 
        ) 
        boxes = remove_overlapped_boxes(boxes) 
 
        pdf_size = (doc[0].rect.width, doc[0].rect.height) 
        dpi = 300 
        page = doc[page_num] 
        pdf_size   = (page.rect.width, page.rect.height) 
        pix        = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72)) 
        image_size = (pix.width, pix.height) 
 
        # tag each box 
        for b in boxes: 
            b.page_num    = page_num 
            b._pdf_size   = pdf_size 
            b._img_size   = image_size 
            b._crop_dir   = para_cropped_dir 
        all_boxes.extend(boxes) 
 
    # 2) process them in parallel (extract→translate→render) 
    translated_boxes: List[Box] = [] 
    render_lock = Lock() 
    with ThreadPoolExecutor(max_workers=8) as exe: 
        def process_and_render(box: Box) -> List[Box]: 
            # scale coords 
            box.coords = scale_img_box_to_pdf_box( 
                box.coords, box._img_size, box._pdf_size 
            ) 
 
            pdf_boxes: List[Box] = [] 
 
            if box.label == BoxLabel.TABLE: 
                pdf_boxes = get_content_in_region(doc, [box]) 
                # calculate the average font size for table contents 
                avg_font_size = get_avg_font_size_by_boxes(pdf_boxes, doc[box.page_num]) 
            else: 
                # for paragraphs / formulas use your OCR/LaTeX extractor 
                pdf_boxes = [extract_content_from_single_image(box, box._crop_dir, api_manager)] 
 
            # 3) translate whatever content we got 
            pdf_boxes = [translate_single_box(box, api_manager) for box in pdf_boxes] 
 
            # 4) render it back into the PDF under a lock 
            with render_lock: 
                for pdf_box in pdf_boxes: 
                    if pdf_box.label == BoxLabel.TABLE: 
                        insert_translated_table_text(doc, pdf_box, font_path, avg_font_size) 
                    else: 
                        add_selectable_latex_to_pdf( 
                            pdf_path, 
                            output_dir / f"{file_id}.pdf", 
                            pdf_box.translation, 
                            pdf_box, 
                            doc, 
                            pdf_box.page_num, 
                            get_avg_font_size_overlapped(pdf_box.coords, doc[pdf_box.page_num]), 
                        ) 
 
                return pdf_boxes 
            
        futures = [exe.submit(process_and_render, b) for b in all_boxes] 

        for f in as_completed(futures): 
            try: 
                translated_boxes.extend(f.result()) 
            except Exception as e: 
                logger.error(f"Error processing box: {e}")
            _ = f.result(timeout=15) 
 
    doc.save(output_dir/f"{file_id}.pdf") 
    doc.close() 
        
    with open(output_dir/f"{file_id}.json", "w") as f: 
        json.dump([asdict(box) for box in translated_boxes], f, indent=4,  default=lambda o: str(o))  # convert Paths (and any other unknown) to string 
 
def main(): 
    parser = argparse.ArgumentParser(description="Translate PDF using Gemini API") 
    parser.add_argument("pdf_path", type=str, help="Path to the input PDF file") 
    parser.add_argument("output_root", type=str, help="Path to the output directory") 
    args = parser.parse_args() 
 
    pdf_path = Path(args.pdf_path) 
    output_root = Path(args.output_root) 
 
    run_pipeline(pdf_path, output_root) 