import csv
import json
import os
import fitz  # PyMuPDF
import random
from pathlib import Path

def load_csv_data(csv_path):
    """Load the submission CSV file with extracted boxes"""
    results = {}
    
    # Read the file directly and process one line at a time
    with open(csv_path, 'r', encoding='utf-8') as f:
        # Skip header
        next(f)
        
        for line in f:
            # Find the first comma that separates id from JSON
            first_comma_pos = line.find(',')
            if (first_comma_pos > 0):
                file_id = line[:first_comma_pos].strip()
                json_data = line[first_comma_pos+1:].strip()
                
                # Skip empty rows
                if not file_id:
                    continue
                
                try:
                    # Try direct JSON parsing
                    boxes = json.loads(json_data)
                    results[file_id] = boxes
                    print(f"Successfully parsed data for {file_id}")
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON for {file_id}: {e}")
    
    return results

def draw_boxes_on_pdf(pdf_path, boxes, output_path):
    """Draw bounding boxes on a PDF file and save to output_path"""
    # Open the PDF
    doc = fitz.open(pdf_path)
    
    # Generate random colors for each block type
    color_map = {}
    
    # Loop through each page and draw boxes
    for box in boxes:
        page_num = box.get("Page", 1)
        if page_num <= 0 or page_num > len(doc):
            print(f"Page {page_num} out of range for {pdf_path}")
            continue
            
        # Get the page (0-indexed)
        page = doc[page_num - 1]
        
        # Get box coordinates
        x = box.get("x", 0)
        y = box.get("y", 0)
        width = box.get("width", 0)
        height = box.get("height", 0)
        
        # IMPORTANT: Convert from PDFPig coordinates to PyMuPDF coordinates
        # Get page height for coordinate conversion
        # page_height = page.rect.height
        
        # Flip the Y coordinate and adjust for height
        # y_converted = page_height - y - height
        
        # Get block type for coloring
        block_type = box.get("blockType", "unknown")
        if block_type not in color_map:
            # Generate a random color for this block type
            color_map[block_type] = (
                random.random(),  # R
                random.random(),  # G
                random.random()   # B
            )
        
        # Get the color for this block type
        color = color_map[block_type]
        
        # Draw rectangle using the converted coordinates
        rect = fitz.Rect(x, y, x + width, y + height)
        page.draw_rect(rect, color=color, width=0.5)
    
    # Add a legend for the colors
    last_page = doc[-1]
    y_pos = 30
    
    for block_type, color in color_map.items():
        legend_rect = fitz.Rect(30, y_pos, 70, y_pos + 15)
        last_page.draw_rect(legend_rect, color=color, width=0.5, fill=color)
        last_page.insert_text((75, y_pos + 10), block_type, fontsize=10)
        y_pos += 20
    
    # Save the output PDF
    doc.save(output_path)
    doc.close()
    print(f"Created visualization at {output_path}")

def main():
    # Paths
    csv_path = "submission_pdfpig.csv"
    pdf_dir = Path("../data/test/testing")  # Adjust this path to your PDFs
    output_dir = Path("visualized_pdfs")
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Load CSV data
    box_data = load_csv_data(csv_path)
    
    # Process each entry
    for file_id, boxes in box_data.items():
        pdf_path = pdf_dir / f"{file_id}.pdf"
        
        # Check if PDF exists, if not, try with .coco_standard suffix
        if not pdf_path.exists():
            pdf_path = pdf_dir / f"{file_id}.coco_standard.pdf"
        
        if pdf_path.exists():
            output_path = output_dir / f"{file_id}_visualized.pdf"
            draw_boxes_on_pdf(pdf_path, boxes, str(output_path))
        else:
            print(f"PDF file not found for {file_id}")

if __name__ == "__main__":
    main()