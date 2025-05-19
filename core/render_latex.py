# Add these lines to the script file
# sudo apt update
# sudo apt install texlive-latex-base texlive-extra-utils

import fitz  # PyMuPDF
import subprocess
import tempfile
import os
import shutil
import logging

logger = logging.getLogger(__name__)

def add_selectable_latex_to_pdf(input_pdf, output_pdf, equation, x, y, page_num=0, fontsize=12):
    # …
    temp_dir = tempfile.mkdtemp()
    try:
        # Write a minimal article (no preview package)
        latex_file = os.path.join(temp_dir, "equation.tex")
        with open(latex_file, "w") as f:
            f.write(r"""
\documentclass{article}
\usepackage[utf8]{inputenc}
\usepackage{amsmath,amssymb}
\pagestyle{empty}
\begin{document}
\[
""" + equation + r"""
\]
\end{document}
""")

        # Compile
        try:
            subprocess.run(
                ["pdflatex", "-interaction=batchmode", "-output-directory", temp_dir, latex_file],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError as e:
            log_path = os.path.join(temp_dir, "equation.log")
            log_tail = ""
            if os.path.exists(log_path):
                with open(log_path, errors="ignore") as lf:
                    log_tail = "".join(lf.readlines()[-30:])
            raise RuntimeError(f"pdflatex failed ({e.returncode}). Last lines:\n{log_tail}")

        # Crop whitespace if pdfcrop is installed
        eq_pdf = os.path.join(temp_dir, "equation.pdf")
        cropped = os.path.join(temp_dir, "equation-crop.pdf")
        try:
            subprocess.run(
                ["pdfcrop", eq_pdf, cropped],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            eq_pdf = cropped
        except FileNotFoundError:
            logger.warning("pdfcrop not found; using uncropped equation.pdf")
        except subprocess.CalledProcessError:
            logger.warning("pdfcrop failed; using uncropped equation.pdf")

        # Embed into source PDF
        src_doc = fitz.open(input_pdf)
        eq_doc = fitz.open(eq_pdf)
        eq_rect = eq_doc[0].rect
        print(eq_rect)
        page = src_doc[page_num]
        target = fitz.Rect(x, y, x + eq_rect.width, y + eq_rect.height)
        print(target)
        page.show_pdf_page(target, eq_doc, 0)
        src_doc.save(output_pdf)
        src_doc.close()
        eq_doc.close()

    finally:
        shutil.rmtree(temp_dir)
        
# Example usage
# add_selectable_latex_to_pdf(
#     'sample.pdf', 
#     'output_selectable.pdf', 
#     r"I _ { 2 } ( x, y, z, w ) = \frac { - 4 z ^ { 2 } } { z ^ { 2 } - w ^ { 2 } } \int _ { 0 } ^ { \infty } u d u \left\{ \frac { B _ { 1 } ( - u ; x, y ) - B _ { 1 } ( - u ; 0, y ) } { x ^ { 2 } } \right\} ^ { 2 } \left( \frac { z ^ { 2 } } { u + z ^ { 2 } } - \frac { w ^ { 2 } } { u + w ^ { 2 } } \right)", 
#     1,1,0, fontsize=10
# )


def overwrite_text_in_pdf(
    input_pdf: str,
    output_pdf: str,
    translation: str,
    rect: fitz.Rect,
    page_num: int = 0,
    fontname: str = "helv",
    fontsize: float = 12,
    color: tuple = (0, 0, 0),
    use_redact: bool = False,
):
    """
    Overwrite text in `rect` on page `page_num` with `translation`.
    If use_redact is True, will use a true redaction (removes content under).
    Otherwise just draws a white box and writes on top.
    """
    doc = fitz.open(input_pdf)
    page = doc[page_num]

    if use_redact:
        # mark for redaction
        page.add_redact_annot(rect, fill=(1, 1, 1))
        page.apply_redactions()
    else:
        # simply cover it with white
        page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))

    # insert the translated text (word‐wraps inside rect)
    page.insert_textbox(
        rect,
        translation,
        fontname=fontname,
        fontsize=fontsize,
        color=color,
        align=fitz.TEXT_ALIGN_LEFT,
    )

    doc.save(output_pdf)
    doc.close()
    
    
overwrite_text_in_pdf(
    "sample.pdf",
    "translated.pdf",
    "This is a sample text!",        # your translation
    fitz.Rect(200, 200, 300, 300),            # bounding box of original text
    page_num=0,
    fontsize=10,
    fontname="helv",
    use_redact=True                  # or False if you just want a cover‐up
)