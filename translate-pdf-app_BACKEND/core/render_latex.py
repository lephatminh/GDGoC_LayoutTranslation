# Add these lines to the script file
# sudo apt update
# sudo apt install texlive-latex-base texlive-extra-utils
# sudo apt install fonts-noto fonts-noto-cjk fonts-noto-extra fonts-dejavu
# sudo apt install texlive-latex-extra  # for polyglossia package

from PyPDF2 import PdfReader, PdfWriter, Transformation
from pathlib import Path
from core.box import Box
from core.box import BoxLabel
import fitz  
import subprocess
import tempfile
import os
import shutil
import logging
import copy

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


def crop_equation_pdf(input_pdf: str, output_pdf: str, margin=5):
    """
    Crop whitespace from a PDF file using pdfcrop.

    Args:
        input_pdf (str): Path to the input PDF file
        output_pdf (str): Path where the cropped PDF will be saved
        margin (int): Margin to add around the cropped content (default: 5 points)

    Returns:
        str: Path to the cropped PDF file
    """
    result = subprocess.run(
        ["pdfcrop", "--margin", str(margin), input_pdf, output_pdf],
        check=False, 
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    
    # Check if pdfcrop succeeded AND actually created the file
    if result.returncode == 0 and os.path.exists(output_pdf):
        logger.info(f"pdfcrop succeeded: {output_pdf}")
        return output_pdf
    else:
        logger.error(f"pdfcrop failed or did not create output file: {output_pdf}")
        # Method 2: Fallback to PyMuPDF
        if crop_pdf_to_content(input_pdf, output_pdf, margin):
            return output_pdf
        
        # Method 3: Last resort - return original
        logger.warning("All cropping methods failed; using original PDF")
        return input_pdf


def crop_pdf_to_content(input_pdf: str, output_pdf: str, margin: int = 5) -> bool:
    """
    Crop PDF to content bounds using PyMuPDF. More reliable than pdfcrop.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        doc = fitz.open(input_pdf)
        page = doc[0]
        
        # Method 1: Use text blocks (best for text content)
        blocks = page.get_text("blocks")
        if blocks:
            # Get bounding box of all text
            bbox = fitz.Rect()
            for block in blocks:
                bbox |= fitz.Rect(block[:4])
            
            # Add margin
            bbox = fitz.Rect(
                bbox.x0 - margin, 
                bbox.y0 - margin,
                bbox.x1 + margin, 
                bbox.y1 + margin
            )
            
            # Ensure bbox is within page bounds
            bbox &= page.rect
            
            # Apply crop
            page.set_cropbox(bbox)
            doc.save(output_pdf)
            doc.close()
            return True
            
    except Exception as e:
        logger.error(f"PyMuPDF cropping failed: {e}")
        return False
    
    return False


def add_selectable_latex_to_pdf(input_pdf: Path,
                                output_pdf: Path,
                                box: Box,
                                src_doc: fitz.Document,
                                page_num=0,
                                fontsize=12,
                                debug=False):  # Add debug parameter
    
    translation = box.translation or ""
    if not translation.strip():
        # If the translated text is empty, skip this box
        return

    x_left_target, y_left_target, x_right_target, y_right_target = box.coords

    logger.info("Params:  %d, %d, %d, %d, %d", 
                box.label, x_left_target, y_left_target, x_right_target, y_right_target)
    
    logger.info(f"Adding LaTeX to PDF: {fontsize}")
    
    # Step 0: Check for condition of left and right point
    if x_left_target > x_right_target:
        raise ValueError("x_left_target must be smaller than x_right_target")

    if y_left_target > y_right_target:
        raise ValueError("y_left_target must be smaller than y_right_target")

    # Step 1: Set up the LaTeX code based on type
    if box.label == BoxLabel.TITLE:
        translation = r"\begin{center}" + translation + r"\end{center}"

    LaTex_format = r"""
            \documentclass{article}
            \usepackage{amsmath}
            \usepackage{amssymb}
            \usepackage{fontspec}

            \usepackage[x11names]{xcolor}
            \usepackage{bibentry}
            \usepackage[hidelinks,breaklinks]{hyperref}
            \usepackage{xurl}

            \setmainfont{Noto Serif}[
                BoldFont = Noto Serif Bold,
                ItalicFont = Noto Serif Italic,
                BoldItalicFont = Noto Serif Bold Italic
            ]

            \sloppy 
            \usepackage{longtable} 
            \usepackage{bookmark} 
            \usepackage{booktabs}      
            \usepackage{array}         
            \usepackage{tabularx}      
            \usepackage{longtable}     
            \usepackage{multirow}      
            \renewcommand{\arraystretch}{1.2} 
            \setlength{\tabcolsep}{8pt} 

            \usepackage{natbib}
            \usepackage{unicode-math}
            \setmathfont{Latin Modern Math}

            \pagestyle{empty}

            \newfontfamily\cjkfont{Noto Sans CJK SC}[Scale=0.9]
            \newfontfamily\arabicfont{Noto Sans Arabic}[Scale=0.9]
            \newfontfamily\vietnamesefont{Noto Serif}[Scale=1.0]
            \newfontfamily\koreanfont{Noto Sans CJK KR}[Scale=0.9]
            \newfontfamily\russianfont{Noto Serif}[Scale=1.0]

            \newcommand{\vi}[1]{{\vietnamesefont\selectlanguage{vietnamese}#1}}
            \newcommand{\zh}[1]{{\cjkfont #1}}
            \newcommand{\ja}[1]{{\cjkfont #1}}
            \newcommand{\ko}[1]{{\koreanfont #1}}
            \newcommand{\ar}[1]{{\arabicfont #1}}
            \newcommand{\ru}[1]{{\russianfont\selectlanguage{russian}#1}}
            \newcommand{\fr}[1]{\selectlanguage{french}#1}
            \newcommand{\de}[1]{\selectlanguage{german}#1}
            \newcommand{\es}[1]{\selectlanguage{spanish}#1}
            \newcommand{\ita}[1]{\selectlanguage{italian}#1}
            
            \begin{document}
            \fontsize{%dpt}{%.1fpt}\selectfont
            %s
            \end{document}
            """ % (fontsize, fontsize * 1.2, translation)

    if debug:
        # Use a predictable directory for debugging
        debug_base = Path("./latex_debug")
        debug_base.mkdir(exist_ok=True)
        temp_dir = str(debug_base / f"box_{box.page_num}_{id(box)}")
        os.makedirs(temp_dir, exist_ok=True)
    else:
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
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        except subprocess.CalledProcessError as e:
            log_path = os.path.join(temp_dir, "equation.log")
            log_tail = ""
            if os.path.exists(log_path):
                with open(log_path, errors="ignore") as lf:
                    log_tail = "".join(lf.readlines()[-30:])
            raise RuntimeError(f"xelatex failed ({e.returncode}). Last lines:\n{log_tail}")

        # Step 4: Crop whitespace if pdfcrop is installed
        eq_pdf = os.path.join(temp_dir, "equation.pdf")
        cropped = os.path.join(temp_dir, "equation-crop.pdf")
        
        if not os.path.exists(eq_pdf):
            raise FileNotFoundError(f"Compiled PDF not found: {eq_pdf}")
        
        eq_pdf = crop_equation_pdf(eq_pdf, cropped, margin=5)

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

        eq_doc.close()

    finally:
        if not debug:
            shutil.rmtree(temp_dir)
        else:
            logger.info(f"Debug: Files preserved in {temp_dir}")