"""PDF processing utilities."""

import copy
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter, Transformation
import logging

def scale_pdf(input_path, output_path, target_width=1025, target_height=1025):
    """
    Scale a PDF file to the specified dimensions.
    
    Args:
        input_path (Path): Path to the input PDF
        output_path (Path): Path to save the scaled PDF
        target_width (int): Target width in pixels
        target_height (int): Target height in pixels
    
    Returns:
        Path: Path to the scaled PDF if successful, None otherwise
    """
    try:
        # Convert dimensions to points (72 points per inch, assuming 72 DPI)
        target_width_pts = float(target_width)
        target_height_pts = float(target_height)
        
        # Open the source PDF
        reader = PdfReader(str(input_path))
        writer = PdfWriter()
        
        # Process each page (usually just one)
        for page_num in range(len(reader.pages)):
            original_page = reader.pages[page_num]
            
            # Get the original dimensions
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
            
            # Update all the boxes
            page.mediabox.lower_left = (0, 0)
            page.mediabox.upper_right = (target_width_pts, target_height_pts)
            
            for box_type in ["/CropBox", "/TrimBox", "/ArtBox", "/BleedBox"]:
                if box_type in page:
                    if box_type == "/CropBox":
                        page.cropbox.lower_left = (0, 0)
                        page.cropbox.upper_right = (target_width_pts, target_height_pts)
                    elif box_type == "/TrimBox":
                        page.trimbox.lower_left = (0, 0)
                        page.trimbox.upper_right = (target_width_pts, target_height_pts)
                    elif box_type == "/ArtBox":
                        page.artbox.lower_left = (0, 0)
                        page.artbox.upper_right = (target_width_pts, target_height_pts)
                    elif box_type == "/BleedBox":
                        page.bleedbox.lower_left = (0, 0)
                        page.bleedbox.upper_right = (target_width_pts, target_height_pts)
            
            # Add the scaled page to the output PDF
            writer.add_page(page)
        
        # Write the result to the output file
        with open(output_path, "wb") as output_file:
            writer.write(output_file)
        
        logging.info(f"PDF scaled successfully to {target_width}x{target_height}. Saved to {output_path}")
        return output_path
    
    except Exception as e:
        logging.error(f"Error scaling PDF {input_path}: {str(e)}")
        return None