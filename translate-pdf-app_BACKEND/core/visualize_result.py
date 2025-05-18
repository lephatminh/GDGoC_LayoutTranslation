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
        x, y, w, h = map(float, [box["x"], box["y"], box["width"], box["height"]])
        translated_text = box.get("text_vi", "")

        # cover the original text area
        rect = fitz.Rect(x, y, x + w, y + h)
        page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
        # page.draw_rect(rect, color=(1, 0, 0), width = 0.5, fill = (1, 1, 1))

        # starting font size (fallback to 12 if missing)
        font_size = box.get("font", {}).get("size", 12)
        min_size  = 4            # don’t shrink below this
        text      = translated_text

        # pre‐compute font metrics constants
        asc_units = meas_font.ascender   # units above baseline
        desc_units= meas_font.descender  # units below baseline (negative)

        stroke = 1      # pts of border_width
        # shrink until it fits horizontally AND vertically
        while font_size > min_size:
            # 1) measure width at this size
            text_width = meas_font.text_length(text, fontsize=font_size)
            # 2) compute actual line‐height in points
            line_height = (asc_units - desc_units) / 1000 * font_size

            # add both sides of the stroke before comparing
            if text_width + 2*stroke <= w and line_height <= h:
                break
            font_size -= 1

        # now center‐vertically
        baseline_y = y + (h - line_height) / 2 + line_height

        # insert the text
        page.insert_text(
            (x, baseline_y),
            text,
            fontname="Roboto",
            fontsize=font_size,
            fontfile=str(font_path),
            color=(0,0,0),
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
        page = doc[mb.get("page", 1) -1]
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