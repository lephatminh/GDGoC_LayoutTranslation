import csv
import json
import os
import fitz  # PyMuPDF
import random
from pathlib import Path
import sys

def load_csv_data(csv_path):
    """Load the submission CSV file with extracted boxes"""
    results = {}
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Skip header
            header = f.readline()
            
            for line in f:
                # Find the first real comma that separates id from solution
                # The challenge here is that there's a comma after "id" in the header
                parts = line.split(',', 1)  # Split only on the first comma
                    
                file_id = parts[0].strip()
                json_data = parts[1].strip()
                
                # Remove any leading/trailing quotes if present
                if json_data.startswith('"') and json_data.endswith('"'):
                    json_data = json_data[1:-1]
                
                # Replace escaped quotes with regular quotes
                json_data = json_data.replace('\\"', '"')
                json_data = json_data.replace('""', '"')
                
                try:
                    boxes = json.loads(json_data)
                    results[file_id] = boxes
                    print(f"Successfully parsed data for {file_id}")
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON for {file_id}: {e}")
                    # Write the problematic JSON to a file for debugging
                    with open(f"{file_id}_debug.json", 'w', encoding='utf-8') as debug_file:
                        debug_file.write(json_data)
                    print(f"Wrote problematic JSON to {file_id}_debug.json")
    except Exception as e:
        print(f"Error reading CSV file: {e}")
    
    return results

def draw_boxes_on_pdf(pdf_path, boxes, output_path):
    """Draw bounding boxes on a PDF file and save to output_path"""
    # Open the PDF
    doc = fitz.open(pdf_path)
    
    # Generate random colors for each block type
    color_map = {}
    
    # Process each page
    processed_pages = set()
    
    # Loop through each box and draw it
    for box in boxes:
        # Get page number (default to 1 if not specified)
        page_num = box.get("Page", 1)
        if page_num <= 0 or page_num > len(doc):
            print(f"Page {page_num} out of range for {pdf_path}")
            continue
            
        # Get the page (0-indexed)
        page = doc[page_num - 1]
        processed_pages.add(page_num - 1)
        
        # Get box coordinates
        x = float(box.get("x", 0))
        y = float(box.get("y", 0))
        width = float(box.get("width", 0))
        height = float(box.get("height", 0))
        
        # Get block type
        block_type = box.get("BlockType", "paragraph")
        
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
        rect = fitz.Rect(x, y, x + width, y + height)
        page.draw_rect(rect, color=color, width=0.5)
    
    # Add a legend for the colors on each processed page
    for page_idx in processed_pages:
        page = doc[page_idx]
        y_pos = 30
        
        for block_type, color in color_map.items():
            legend_rect = fitz.Rect(30, y_pos, 70, y_pos + 15)
            page.draw_rect(legend_rect, color=color, width=0.5, fill=color)
            page.insert_text((75, y_pos + 10), block_type, fontsize=10)
            y_pos += 20
    
    # Save the output PDF
    doc.save(output_path)
    doc.close()
    print(f"Created visualization at {output_path}")

def find_pdf_file(file_id, search_dirs):
    """Search for a PDF file with the given ID in multiple directories"""
    for dir_path in search_dirs:
        # Try different possible filenames
        possible_names = [
            f"{file_id}.pdf",
            f"{file_id}.coco_standard.pdf"
        ]
        
        for name in possible_names:
            pdf_path = dir_path / name
            if pdf_path.exists():
                return pdf_path
    
    return None

def main():
    csv_path = "submission_test.csv"  # Default
    
    # Possible PDF directories to search
    search_dirs = [
        Path("data/test/PDF_scaled"),
    ]
    
    # Create output directory
    output_dir = Path("visualized_pdfs")
    output_dir.mkdir(exist_ok=True)
    
    # Load CSV data
    print(f"Loading data from {csv_path}...")
    box_data = load_csv_data(csv_path)
    
    if not box_data:
        print("No data was loaded from the CSV file.")
        return
    
    print(f"Successfully loaded data for {len(box_data)} documents")
    
    # Process each document
    for file_id, boxes in box_data.items():
        print(f"Processing {file_id}...")
        
        # Find PDF file
        pdf_path = find_pdf_file(file_id, search_dirs)
        
        if pdf_path:
            print(f"Found PDF: {pdf_path}")
            output_path = output_dir / f"{file_id}_visualized.pdf"
            
            try:
                draw_boxes_on_pdf(pdf_path, boxes, str(output_path))
            except Exception as e:
                print(f"Error drawing boxes: {e}")
        else:
            print(f"PDF file not found for {file_id}")
    
    print("Visualization complete!")

if __name__ == "__main__":
    main()