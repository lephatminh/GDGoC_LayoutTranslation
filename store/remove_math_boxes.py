import csv
import json
from core.csv_utils import load_csv_data_pymupdf
from typing import List, Dict, Any, Tuple
from pathlib import Path
from core.extract_math_boxes import load_math_boxes
from core.filter_math_related_boxes import filter_text_boxes, save_filtered_boxes

def main():
    # File paths
    ocr_csv = "submission_ocr_official.csv"
    math_notation_dir = Path("YOLO_Math_detection")
    output_csv = "submission_ocr_no_math.csv"
    
    # Load OCR text boxes
    print("Loading OCR text boxes...")
    ocr_data = load_csv_data_pymupdf(ocr_csv)
    print(f"Loaded {len(ocr_data)} files from OCR data")
    
    # Process each file
    filtered_data = {}
    for file_id, text_boxes in ocr_data.items():
        print(f"Processing {file_id}...")
        
        # Load math boxes for this file
        math_boxes = load_math_boxes(math_notation_dir, file_id)
        print(f"  Found {len(math_boxes)} math boxes")
        
        # Filter text boxes
        filtered_boxes = filter_text_boxes(text_boxes, math_boxes)
        print(f"  Kept {len(filtered_boxes)} of {len(text_boxes)} text boxes")
        
        # Store filtered boxes
        filtered_data[file_id] = filtered_boxes
    
    # Save filtered data
    save_filtered_boxes(filtered_data, output_csv)
    print("Done!")

if __name__ == "__main__":
    main()