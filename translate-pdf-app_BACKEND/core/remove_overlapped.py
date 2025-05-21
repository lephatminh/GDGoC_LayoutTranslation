from core.box import Box
from typing import List
import logging

def is_overlap(box1: Box, box2: Box) -> bool:
    """Check if two boxes overlap."""
    x1, y1, x2, y2 = box1.coords
    x3, y3, x4, y4 = box2.coords

    if (x1 == x3 and x2 == x4) and (y1 == y3 and y2 == y4):
        return True

    return x1 < x4 and x3 < x2 and y1 < y4 and y3 < y2

def calculate_area(box: Box) -> float:
    """Calculate the area of a box given [top_left_x, top_left_y, bottom_right_x, bottom_right_y]."""
    x1, y1, x2, y2 = box.coords
    return (x2 - x1) * (y2 - y1)

def remove_overlapped_boxes(boxes: List[Box]) -> List[Box]:
    """Remove boxes that are overlapped by others, keeping the one with larger area."""
    n = len(boxes)
    # Track boxes to keep (initially all)
    keep = set(range(n))

    # Check each pair of boxes
    for i in range(n):
        for j in range(i+1,n):
            if i in keep and j in keep and is_overlap(boxes[i], boxes[j]):
                # If boxes overlap, remove the one with smaller area
                area_i = calculate_area(boxes[i])
                area_j = calculate_area(boxes[j])
                if area_i <= area_j:
                    keep.discard(i)  # Remove box i (smaller or equal area)
                else:
                    keep.discard(j)  # Remove box j (smaller area)
                
                logging.debug(f"Removed box {j} due to overlap with box {i}.")

    # Return the filtered list of non-overlapping boxes
    return [boxes[i] for i in keep]