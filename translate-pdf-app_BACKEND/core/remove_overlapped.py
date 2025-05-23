from core.box import Box
from typing import List
from rtree import index

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
    """
    Keep only the largest boxes in any overlapping cluster.
    Runs in O(n log n) by sorting + R-tree queries.
    """
    # 1) sort boxes by descending area
    sorted_boxes = sorted(boxes, key=calculate_area, reverse=True)

    # 2) build R-tree index
    idx = index.Index()
    kept: List[Box] = []

    for i, box in enumerate(sorted_boxes):
        x1, y1, x2, y2 = box.coords
        # query any already-kept box that intersects this one
        hits = list(idx.intersection((x1, y1, x2, y2)))
        if not hits:
            # no overlap → keep this box
            kept.append(box)
            idx.insert(len(kept)-1, (x1, y1, x2, y2))

    return kept