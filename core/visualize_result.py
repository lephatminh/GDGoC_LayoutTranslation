import fitz

def visualize_translation_and_math(pdf_path, translated_boxes, math_boxes, output_path, font_path):
    """
    Insert translated text and math boxes into the original PDF.

    Args:
        pdf_path (str or Path): Path to the input PDF.
        translated_boxes (list of dict): Each dict contains x, y, width, height, text_vi, page, and optionally font size.
        math_boxes (list of dict): Each dict contains x, y, width, height, and page for math regions.
        output_path (str or Path): Path where the output PDF will be saved.
        font_path (str or Path): Path to the font file for rendering text.
    """
    doc = fitz.open(str(pdf_path))

    # also keep a simple Font object for measuring string widths
    meas_font = fitz.Font(fontfile=str(font_path))
    
    # Insert translated text
    for box in translated_boxes:
        page_idx = box.get("page", 1) - 1
        page = doc[page_idx]
        x, y, w, h = box["x"], box["y"], box["width"], box["height"]
        text = box.get("text_vi", "")

        # cover the original text area
        rect = fitz.Rect(x, y, x + w, y + h)
        page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))

        # determine font size
        font_size = box.get("font", {}).get("size", 12)
        text_width = meas_font.text_length(text, fontsize=font_size)
        while text_width > w and font_size > 1:
            font_size -= 1
            text_width = meas_font.text_length(text, fontsize=font_size)

        # insert the translated text
        page.insert_text((x, y + h),
                         text,
                         fontname='Roboto',
                         fontsize=font_size,
                         fontfile=str(font_path),
                         color=(0, 0, 0),
                        #  encoding='utf-16',
                         fill_opacity=1,
                         stroke_opacity=1,
                         border_width=1,
                        )

    # Highlight math regions
    for mb in math_boxes:
        page_idx = mb.get("page", 1) - 1
        page = doc[page_idx]
        x, y, w, h = mb["x"], mb["y"], mb["width"], mb["height"]
        rect = fitz.Rect(x, y, x + w, y + h)
        page.draw_rect(rect, color=(1, 0, 0), width=1)

    doc.save(str(output_path))


import fitz
from pathlib import Path

def insert_translated_text(doc: fitz.Document,
                           translated_boxes: list[dict],
                           font_path: Path):
    """
    Insert translated text and math boxes into the original PDF.

    Args:
        pdf_path (str or Path): Path to the input PDF.
        translated_boxes (list of dict): Each dict contains x, y, width, height, text_vi, page, and optionally font size.
        math_boxes (list of dict): Each dict contains x, y, width, height, and page for math regions.
        output_path (str or Path): Path where the output PDF will be saved.
        font_path (str or Path): Path to the font file for rendering text.
    """

    # also keep a simple Font object for measuring string widths
    meas_font = fitz.Font(fontfile=str(font_path))
    
    # Insert translated text
    for box in translated_boxes:
        page_idx = box.get("page", 1) - 1
        page = doc[page_idx]
        x, y, w, h = box["x"], box["y"], box["width"], box["height"]
        translated_text = box.get("text_vi", "")

        # cover the original text area
        rect = fitz.Rect(x, y, x + w, y + h)
        page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))

        # determine font size
        font_size = box.get("font", {}).get("size", 12)
        text_width = meas_font.text_length(translated_text, fontsize=font_size)
        while text_width > w and font_size > 1:
            font_size -= 1
            text_width = meas_font.text_length(translated_text, fontsize=font_size)

        # insert the translated text
        page.insert_text((x, y + h),
                         translated_text,
                         fontname='Roboto',
                         fontsize=font_size,
                         fontfile=str(font_path),
                         color=(0, 0, 0),
                        #  encoding='utf-16',
                         fill_opacity=1,
                         stroke_opacity=1,
                         border_width=1,
                        )

def insert_math_images(doc: fitz.Document,
                       math_boxes: list[dict],
                       math_img_dir: Path):
    """
    math_img_dir/
      └── <file_id>_translated/
           ├── 1.jpg
           ├── 2.jpg
           └── …
    """
    for mb in math_boxes:
        page = doc[mb["page"]-1]
        x,y,w,h = mb["x"], mb["y"], mb["width"], mb["height"]
        idx = mb.get("index")   # however you numbered your crops
        # build the image path:
        # img = math_img_dir / f"{mb['file_id']}" / f"{idx}.jpg"
        img = math_img_dir / "images" / f"{mb['id']}.jpg"

        if img.exists():
            page.insert_image(fitz.Rect(x,y,x+w,y+h),
                              filename=str(img))
        else:
            # fallback: draw a red box
            page.draw_rect(fitz.Rect(x,y,x+w,y+h),
                            color=(1,0,0), width=1)

def visualize_translation_and_math(pdf_path: Path,
                                   translated_boxes: list[dict],
                                   math_boxes: list[dict],
                                   output_path: Path,
                                   font_path: Path,
                                   math_img_dir: Path):
    doc = fitz.open(str(pdf_path))
    insert_translated_text(doc, translated_boxes, font_path)
    insert_math_images(doc, math_boxes, math_img_dir)
    doc.save(str(output_path))