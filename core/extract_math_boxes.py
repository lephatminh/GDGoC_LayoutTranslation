from typing import List, Dict, Any, Tuple
from pathlib import Path
import os


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
    ]

    txt_file_found = False
    for directory in possible_dirs:
        # Try different file names that might contain the math boxes
        possible_files = [
            directory / "pdf_coor.txt",                 # Standard format
        ]

        for txt_path in possible_files:
            if txt_path.exists():
                try:
                    with open(txt_path, 'r') as f:
                        for line in f:
                            parts = line.strip().split() # string
                            if (len(parts) == 5):
                                id_, x_left, y_left, x_right, y_right = map(float, parts)

                                box = {
                                    'id': int(id_),
                                    'x': x_left,
                                    'y': y_left,
                                    'width': x_right - x_left,
                                    'height': y_right - y_left,
                                    'page': 1
                                }
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