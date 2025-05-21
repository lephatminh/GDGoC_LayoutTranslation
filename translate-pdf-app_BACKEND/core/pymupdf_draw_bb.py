import json
import fitz  
import random
from pathlib import Path
from core.box import Box
from typing import List
from core.pdf_utils import scale_img_box_to_pdf_box

def draw_boxes_on_pdf(pdf_path: Path, boxes: List[Box], output_path: Path):
    """Draw bounding boxes on a PDF file and save to output_path"""
    # Open the PDF
    doc = fitz.open(pdf_path)
    
    # Generate random colors for each block type
    color_map = {}
    
    # Process each page
    processed_pages = set()

    # Capture the original PDF size
    pdf_size = (doc[0].rect.width, doc[0].rect.height)
    
    # Loop through each box and draw it
    for box in boxes:
        # use the page_num attribute
        page_num = box.page_num or 1
        if page_num < 1 or page_num > len(doc):
            continue
            
        # Get the page (0-indexed)
        page = doc[page_num - 1]

        dpi = 300
        pdf_w, pdf_h = page.rect.width, page.rect.height
        pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
        img_w, img_h = pix.width, pix.height
        scaled_x1, scaled_y1, scaled_x2, scaled_y2 = scale_img_box_to_pdf_box(box.coords, (img_w, img_h), (pdf_w, pdf_h))

        processed_pages.add(page_num)
        
        # use label enum or define your own block type string
        block_type = box.label
        
        # Generate color for this block type if not already done

        if block_type not in color_map:
            color_map[block_type] = (
                random.random(),  # R
                random.random(),  # G
                random.random()   # B
            )
        
        # Get the color for this block type
        
        color = color_map[block_type]
        
        # Draw rectangle using coordinates directly
        # Create rect with (x0, y0, x1, y1) - top-left and bottom-right points
        rect = fitz.Rect(scaled_x1, scaled_y1, scaled_x2, scaled_y2)
        page.draw_rect(rect, color=color, width=1.5)
    
    # Add a legend for the colors on each processed page
    for page_idx in processed_pages:
        page = doc[page_idx - 1]
        y_pos = 30
        
        for block_type, color in color_map.items():
            legend_rect = fitz.Rect(30, y_pos, 70, y_pos + 15)
            page.draw_rect(legend_rect, color=color, width=0.5, fill=color)
            # page.insert_text((75, y_pos + 10), block_type, fontsize=10)
            y_pos += 20
    
    # Save the output PDF
    doc.save(output_path)
    doc.close()
    print(f"Created visualization at {output_path}")