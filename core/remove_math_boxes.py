import csv
import json
from typing import List, Dict, Any
from pathlib import Path

MARGINAL_ERROR_VERTICAL = 9  # 5 points vertical margin
MARGINAL_ERROR_HORIZONTAL = 9  # 3 points horizontal margin
        
def is_inside_math_box(pymupdf_box: Dict[str, float], math_box: Dict[str, float]) -> bool:
    """
    Check if two bounding boxes overlap
    
    Args:
        box1: First bounding box {x, y, width, height, page}
        box2: Second bounding box {x, y, width, height, page}
        
    Returns:
        True if boxes overlap, False otherwise
    """

    # Check if the boxes are on the same page
    if pymupdf_box.get("page", 1) != math_box.get("page", 1):
        return False
    
    # Extract coordinates
    x1_1 = pymupdf_box["x"]
    y1_1 = pymupdf_box["y"]
    x2_1 = x1_1 + pymupdf_box["width"]
    y2_1 = y1_1 + pymupdf_box["height"]
    
    x1_2 = math_box["x"] - MARGINAL_ERROR_HORIZONTAL 
    y1_2 = math_box["y"] - MARGINAL_ERROR_VERTICAL
    x2_2 = x1_2 + math_box["width"] + (2 * MARGINAL_ERROR_HORIZONTAL) 
    y2_2 = y1_2 + math_box["height"] + (2 * MARGINAL_ERROR_VERTICAL)

    overlap = (
        x1_2 <= x1_1 and
        x2_2 >= x2_1 and
        y1_2 <= y1_1 and
        y2_2 >= y2_1
    )

    return overlap

def filter_text_boxes(text_boxes: List[Dict[str, Any]], 
                      math_boxes: List[Dict[str, float]]) -> List[Dict[str, Any]]:
    """
    Filter out text boxes that overlap with math notation boxes
    
    Args:
        text_boxes: List of text bounding boxes from OCR
        math_boxes: List of math notation bounding boxes
        
    Returns:
        List of text boxes that don't overlap with any math boxes
    """
    filtered_boxes = []
    
    for text_box in text_boxes:
        # Check if the text box overlaps with any math box
        overlaps_with_math = False
        for math_box in math_boxes:
            if is_inside_math_box(text_box, math_box):
                overlaps_with_math = True
                break
        
        # If it doesn't overlap with any math box, keep it
        if not overlaps_with_math:
            filtered_boxes.append(text_box)
    
    return filtered_boxes

def save_filtered_boxes(filtered_data: Dict[str, List[Dict[str, Any]]], output_csv: str):
    """
    Save filtered text boxes to CSV
    
    Args:
        filtered_data: Dictionary mapping file IDs to filtered text boxes
        output_csv: Path to output CSV file
    """
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["id", "solution"])
        
        for file_id, boxes in filtered_data.items():
            json_str = json.dumps(boxes, ensure_ascii=False)
            writer.writerow([file_id, json_str])