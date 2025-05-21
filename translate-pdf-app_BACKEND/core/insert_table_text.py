import fitz
from pathlib import Path
from typing import List
from core.box import Box

def insert_translated_table_text(doc: fitz.Document,
                           table_box: Box,
                           font_path: Path) -> None:
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
    page_idx = table_box.page_num
    page = doc[page_idx]
    x1, y1, x2, y2 = table_box.coords
    box_width = x2 - x1

    translated_text = str(table_box.translation)

    if translated_text == "":
        # If the translated text is empty, skip this box
        return

    # cover the original text area
    rect = fitz.Rect(x1, y1, x2, y2)
    # page.draw_rect(rect, color=(0, 0, 0), fill=(1, 1, 1), width = 0.5)

    page.draw_rect(rect, fill=(1, 1, 1), width=0)

    # This is for debug
    #page.draw_rect(rect, color=(0, 0,0), fill=(1, 1, 1))

    # determine font size
    font_size = 12

    text_width = meas_font.text_length(translated_text, fontsize=font_size)
    while text_width > box_width and font_size > 1:
        font_size -= 0.25
        text_width = meas_font.text_length(translated_text, fontsize=font_size)
    
    # center vertically
    line_height = (meas_font.ascender - meas_font.descender) / 1000 * font_size
    # baseline_y = y1 + (y2 - y1 - line_height) / 2 + line_height

    # insert the translated text
    page.insert_text((x1, y2),
                        translated_text,
                        fontname='Roboto',
                        fontsize=font_size,
                        fontfile=str(font_path),
                        color=(0, 0, 0),
                        fill_opacity=1,
                        stroke_opacity=1,
                        border_width=1,
                    )