# Add these lines to the script file
# sudo apt update
# sudo apt install texlive-latex-base texlive-extra-utils

import fitz  # PyMuPDF
import subprocess
import tempfile
import os
import shutil
import logging
import copy
from PyPDF2 import PdfReader, PdfWriter, Transformation
from pathlib import Path
from core.box import Box

logger = logging.getLogger(__name__)

def scale_pdf_properly(input_path, output_path, target_width=1025, target_height=1025):
    """
    Scale a PDF to the target dimensions ensuring both page size and content are scaled.

    Args:
        input_path (str): Path to the input PDF file
        output_path (str): Path where the scaled PDF will be saved
        target_width (int): Target width in pixels (default: 1025)
        target_height (int): Target height in pixels (default: 1025)
    """
    # Read the original PDF
    reader = PdfReader(input_path)
    writer = PdfWriter()

    # Convert target dimensions from pixels to points (72 points = 1 inch)
    # Assuming 72 DPI resolution
    target_width_pts = target_width
    target_height_pts = target_height

    # Process each page
    for page_num in range(len(reader.pages)):
        # Get the original page
        original_page = reader.pages[page_num]

        # Get original page dimensions
        mediabox = original_page.mediabox
        orig_width = float(mediabox.width)
        orig_height = float(mediabox.height)

        # Calculate scaling factors
        width_scale = target_width_pts / orig_width
        height_scale = target_height_pts / orig_height

        # Create a copy of the page to work with
        page = copy.deepcopy(original_page)

        # Apply scaling transformation to the content
        transform = Transformation().scale(width_scale, height_scale)
        page.add_transformation(transform)

        # Update the mediabox to the new dimensions
        # PyPDF2 uses a coordinate system with (0,0) at the bottom left
        page.mediabox.lower_left = (0, 0)
        page.mediabox.upper_right = (target_width_pts, target_height_pts)

        # Also update cropbox and trimbox if they exist
        if "/CropBox" in page:
            page.cropbox.lower_left = (0, 0)
            page.cropbox.upper_right = (target_width_pts, target_height_pts)

        if "/TrimBox" in page:
            page.trimbox.lower_left = (0, 0)
            page.trimbox.upper_right = (target_width_pts, target_height_pts)

        if "/ArtBox" in page:
            page.artbox.lower_left = (0, 0)
            page.artbox.upper_right = (target_width_pts, target_height_pts)

        if "/BleedBox" in page:
            page.bleedbox.lower_left = (0, 0)
            page.bleedbox.upper_right = (target_width_pts, target_height_pts)

        # Add the scaled page to the output PDF
        writer.add_page(page)

    # Write the result to the output file
    with open(output_path, "wb") as output_file:
        writer.write(output_file)

    print(f"PDF scaled successfully to {target_width}x{target_height}.")
    print(f"Both page dimensions and content have been scaled. Saved to {output_path}")


def add_selectable_latex_to_pdf(input_pdf: Path,
                                output_pdf: Path,
                                equation: str,
                                box: Box,
                                src_doc: fitz.Document,
                                page_num=0,
                                fontsize=12):
    '''
    This function is to:
        1. Get the LaTex code from the equation
        2. Create a 'equation.tex' file from the LaTex code
        3. Create a respectively 'equation.pdf'
        4. Do a PDF cropping for 'equation.pdf' (if success, else remain the same)
        5. Scale the PDF to fit the target rectangle
        5.5 Remove the content in the target box first
        6. Insert the scaled 'equation.pdf' into the 'input_pdf' at the
           'x_left_target', 'y_left_target', 'x_right_target', 'y_right_target'
           to the 'input_pdf' PDF and save as 'output_pdf' PDF

    Args:
        input_pdf: str
        output_pdf: str
        equation: str - Latex code of the paragraph or equation
        x_left_target: float - x coord of top left point
        y_left_target: float - y coord of top left point
        x_right_target: float - x coord of bottom right point
        y_right_target: float - y coord of bottom right point
        page_num: int - page number to insert into (0-based)
        fontsize: int - font size

    Output:
        New PDF with inserted LaTex rendered document, scaled to fit the target rectangle
    '''
    x_left_target, y_left_target, x_right_target, y_right_target = box.coords

    logger.info("Params: %s, %s, %d, %d, %d, %d", 
                input_pdf, output_pdf, x_left_target, y_left_target, x_right_target, y_right_target)
    
    logger.info(f"Adding LaTeX to PDF: {fontsize}")
    
    # Step 0: Check for condition of left and right point
    if x_left_target > x_right_target:
        raise ValueError("x_left_target must be smaller than x_right_target")

    if y_left_target > y_right_target:
        raise ValueError("y_left_target must be smaller than y_right_target")

    # Step 1: Set up the LaTeX code based on type
    LaTex_format = ''

    LaTex_format = r"""
            \documentclass{article}
            \usepackage{amsmath,amssymb}
            \usepackage{fontspec}
            \usepackage[x11names]{xcolor}
            \usepackage{bibentry}
            \usepackage[hidelinks,breaklinks]{hyperref}
            \usepackage{xurl}
            \setmainfont{DejaVu Serif}
            \pagestyle{empty}
            \begin{document}
            \fontsize{%dpt}{%.1fpt}\selectfont
            %s
            \end{document}
            """ % (fontsize, fontsize * 1.2, equation)

    temp_dir = tempfile.mkdtemp()
    try:
        # Step 2: Create a 'equation.tex' file from the LaTeX code
        latex_file = os.path.join(temp_dir, "equation.tex")
        with open(latex_file, "w", encoding="utf-8") as f:
            f.write(LaTex_format)

        # Step 3: Compile to create 'equation.pdf'
        try:
            subprocess.run(
                ["xelatex", "-interaction=batchmode", "-output-directory", temp_dir, latex_file],
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

        # Step 4: Crop whitespace if pdfcrop is installed
        eq_pdf = os.path.join(temp_dir, "equation.pdf")
        cropped = os.path.join(temp_dir, "equation-crop.pdf")
        try:
            subprocess.run(
                ["pdfcrop", "--margins", "5", eq_pdf, cropped],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            eq_pdf = cropped
        except FileNotFoundError:
            logger.warning("pdfcrop not found; using uncropped equation.pdf")
        except subprocess.CalledProcessError:
            logger.warning("pdfcrop failed; using uncropped equation.pdf")

        # # Visualize the equation PDF for debugging
        # doc = fitz.open(eq_pdf)
        # page = doc.load_page(0)
        # pix = page.get_pixmap(dpi=150)
        # img_bytes = pix.pil_tobytes("png")
        # img = Image.open(io.BytesIO(img_bytes))
        # img_array = np.array(img)
        # plt.figure(figsize=(20, 20))
        # plt.imshow(img_array)
        # plt.axis("off")
        # plt.show()
        # doc.close()

        eq_doc = fitz.open(eq_pdf)
        eq_page = eq_doc[0]
        eq_rect = eq_page.rect  # Natural size of the equation PDF
        print("Equation natural size:", eq_rect)

        # Define the target rectangle
        target = fitz.Rect(x_left_target, y_left_target, x_right_target, y_right_target)
        print("Target rectangle:", target)

        # Insert the equation PDF into the target page, using keep_proportion to scale
        page = src_doc[page_num]
        page.draw_rect(
            target,
            color = (1,1,1),
            fill = (1,1,1),
            width = 0
        )
        # page.draw_rect(
        #     fitz.Rect(x_left_target, y_left_target, x_right_target, y_right_target),
        #     color=(1, 0, 0),    # red stroke
        #     width=1,            # line thickness in points
        #     fill=None           # no fill
        # )
        # For visualize the scaling
        #page.draw_rect(target, color=(1, 0, 0), fill = (1,1,1) ,width=0.5)
        #eq_page.draw_rect(eq_rect, color=(0, 1, 0) ,width=0.5)
        page.show_pdf_page(target, eq_doc, 0, keep_proportion=False)

        # src_doc.save(str(output_pdf))
        eq_doc.close()

    finally:
        shutil.rmtree(temp_dir)