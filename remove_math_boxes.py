import csv
import json
from core.csv_utils import load_csv_data_pymupdf
from core.img_to_pdf import scale_box_to_pdf
from typing import List, Dict, Any, Tuple
from pathlib import Path

MARGINAL_ERROR_VERTICAL = 9  # 5 points vertical margin
MARGINAL_ERROR_HORIZONTAL = 9  # 3 points horizontal margin

# YOLO_Math_detection/detection.ipynb yields index.txt
# NOTE: index.txt is a troll, please consider a different name
def load_math_boxes(math_notation_dir: Path, file_id: str):
    """
    Load math notation bounding boxes from the YOLO detection outputs
    
    Args:
        math_notation_dir: Directory containing math notation detection results
        file_id: ID of the file to process
        
    Returns:
        List of math bounding boxes in the format {x, y, width, height, page}
    """
    math_boxes = []

    possible_dirs = [
        math_notation_dir / file_id,
        math_notation_dir,
        math_notation_dir / "Math_notation",
        math_notation_dir / "Super_Math_notation"
    ]

    # NOTE: can it be more dynamic instead of hard-coded size
    # PDF coordinate conversion information
    jpg_size = (2550, 3300)  # Default size used in YOLO detection
    pdf_size = (612, 792)    # Default PDF size

    size_found = False
    for dir in possible_dirs:
        size_path = dir / "size.txt"
        if size_path.exists():
            try:
                with open(size_path, 'r') as f:
                    lines = f.readlines()
                    if len(lines) >= 2:
                        jpg_size = eval(lines[0].strip()) 
                        pdf_size = eval(lines[1].strip())
                        size_found = True
                        break
            except Exception as e:
                print(f"Error reading size file: {e}")

    if not size_found:
        print(f"Warning: Could not find size information for {file_id}. Using default sizes.")

    txt_file_found = False
    for directory in possible_dirs:
        # Try different file names that might contain the math boxes
        possible_files = [
            directory / "index.txt",                 # Standard format
            directory / f"{file_id}.txt",            # Named after PDF
            directory / f"{file_id}_boxes.txt",      # Alternative naming
            directory / f"{file_id}_math_boxes.txt"  # Alternative naming
        ]

        for txt_path in possible_files:
            if txt_path.exists():
                try:
                    with open(txt_path, 'r') as f:
                        for line in f:
                            parts = line.strip().split() # string
                            if (len(parts) == 5):
                                box_id, x1, y1, x2, y2 = parts # still string
                                x1, y1, x2, y2 = map(float, [x1, y1, x2, y2])

                                # Convert to PDF coordinates
                                pdf_x1, pdf_y1, pdf_x2, pdf_y2 = scale_box_to_pdf([x1, y1, x2, y2], jpg_size, pdf_size)

                                # Convert to x, y, width, height format
                                math_boxes.append({
                                    "x": pdf_x1,
                                    "y": pdf_y1,
                                    "width": pdf_x2 - pdf_x1,
                                    "height": pdf_y2 - pdf_y1,
                                    "page": 1
                                })
                            # elif(len(parts) == 4):
                
                    txt_file_found = True
                    break
                except Exception as e:
                    print(f"Error reading {txt_path}: {e}")

            if txt_file_found:
                break
        # NOTE: should I use YOLO detection outputs directly
    
    if not txt_file_found:
        print(f"Warning: Could not find math boxes for {file_id}")
    
    return math_boxes
        
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

# if __name__ == "__main__":
#     main()