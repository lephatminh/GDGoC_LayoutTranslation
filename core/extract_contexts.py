from typing import List, Dict, Any, Tuple

def get_contexts(pymupdf_box: Dict[str, Any], pdfpig_boxes: List[Dict[str, Any]]) -> List[str]:
    """
    Get contexts (paragraph texts from pdfpig_boxes) that overlap with a pymupdf bounding box
    
    Args:
        pymupdf_box: A single bounding box from PyMuPDF output
        pdfpig_boxes: List of bounding boxes from PDFPig output
        
    Returns:
        List of paragraph texts that overlap with the PyMuPDF box
    """
    contexts = []

    # Extract pymupdf box coordinates to (x1, y1, x2, y2) format where (x1, y1) is the top-left and (x2, y2) is the bottom-right
    pymupdf_x1 = float(pymupdf_box.get("x", 0))
    pymupdf_y1 = float(pymupdf_box.get("y", 0))
    pymupdf_x2 = pymupdf_x1 + float(pymupdf_box.get("width", 0))
    pymupdf_y2 = pymupdf_y1 + float(pymupdf_box.get("height", 0))

    # Which page the pymupdf box is on
    pymupdf_page = pymupdf_box.get("page", 1)

    # Iterate through all pdfpig_input paragraph bounding boxes
    for pdfpig_box in pdfpig_boxes:
        if pdfpig_box.get("Page", 1) != pymupdf_page:
            continue

        pdfpig_x1 = float(pdfpig_box.get("x", 0))
        pdfpig_y1 = float(pdfpig_box.get("y", 0))
        pdfpig_x2 = pdfpig_x1 + float(pdfpig_box.get("width", 0))
        pdfpig_y2 = pdfpig_y1 + float(pdfpig_box.get("height", 0))
        ## If pymupdf_box is overlapped with the pdfpig_box then append it into contexts
        if (max(pymupdf_x1, pdfpig_x1) < min(pymupdf_x2, pdfpig_x2)and 
            max(pymupdf_y1, pdfpig_y1) < min(pymupdf_y2, pdfpig_y2)):
            contexts.append(pdfpig_box.get("text", ""))

    return contexts

def get_all_contexts(pymupdf_boxes: List[Dict[str, Any]], pdfpig_boxes: List[Dict[str, Any]]) -> Dict[int, List[str]]:
    all_contexts = {}

    for i, pymupdf_box in enumerate(pymupdf_boxes):
        contexts = get_contexts(pymupdf_box, pdfpig_boxes)
        all_contexts[i] = contexts

    return all_contexts    

def get_pymupdf_boxes_from_context(pymupdf_boxes: List[Dict[str, Any]], pdfpig_box: Dict[str, Any]) -> Dict[Tuple[int, int, int, int], str]:
    """
    Find all PyMuPDF boxes that overlap with a given PDFPig box
    
    Args:
        pymupdf_boxes_list: List of bounding boxes from PyMuPDF output
        pdfpig_box: A single bounding box from PDFPig output
        
    Returns:
        Dictionary mapping box index to PyMuPDF box that overlaps with the PDFPig box
    """
    overlapping_boxes = {}

    pdfpig_x1 = float(pdfpig_box.get("x", 0))
    pdfpig_y1 = float(pdfpig_box.get("y", 0))
    pdfpig_x2 = pdfpig_x1 + float(pdfpig_box.get("width", 0))
    pdfpig_y2 = pdfpig_y1 + float(pdfpig_box.get("height", 0))

    # Get page number
    pdfpig_page = pdfpig_box.get("page", 1)

    for pymupdf_box in pymupdf_boxes:
        # Skip if not on the same page
        if pymupdf_box.get("page", 1) != pdfpig_page:
            continue

        pymupdf_x1 = float(pymupdf_box.get("x", 0))
        pymupdf_y1 = float(pymupdf_box.get("y", 0))
        pymupdf_x2 = pymupdf_x1 + float(pymupdf_box.get("width", 0))
        pymupdf_y2 = pymupdf_y1 + float(pymupdf_box.get("height", 0))
    
        if (max(pymupdf_x1, pdfpig_x1) < min(pymupdf_x2, pdfpig_x2) and
            max(pymupdf_y1, pdfpig_y1) < min(pymupdf_y2, pdfpig_y2)):
            
            pymupdf_boxes.insert(pymupdf_box)
    
    return pymupdf_boxes

 