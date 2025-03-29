import fitz  # PyMuPDF
import json
from pathlib import Path
import json

def int_to_rgb(color_int):
    """Convert integer color to RGB tuple."""
    if color_int < 0:
        color_int = color_int & 0xFFFFFFFF

    a = (color_int >> 24) & 0xFF
    r = (color_int >> 16) & 0xFF
    g = (color_int >> 8) & 0xFF
    b = color_int & 0xFF

    if (a == 0):
        a = 255

    return [r, g, b, a]

# Function to extract bounding boxes from a JSON file
def extract_bboxes_from_json(json_file_path):
    # Load the JSON data from the file
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # Extract the bounding boxes (bbox) from the 'cells' section
    bboxes = [cell['bbox'] for cell in data['cells']]
    return bboxes

def extract_pdf_info_with_bounding_boxes(pdf_path, output_json_path=None):
    doc = fitz.open(pdf_path)
    output = {}

    # Extract text cells
    cells = []
    for page_num, page in enumerate(doc, start=1):
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    # Skip empty text
                    if not span["text"].strip():
                        continue

                    # Extract bounding box and text
                    bbox = [
                        span["bbox"][0],
                        span["bbox"][1],
                        span["bbox"][2] - span["bbox"][0],  # width
                        span["bbox"][3] - span["bbox"][1],  # height
                    ]
                    cell = {
                        "bbox": bbox,
                        "text": span["text"].strip(),
                        "font": {
                            "color": int_to_rgb(span["color"]),
                            "name": span["font"],
                            "size": 1,  # Normalized size
                        },
                        "text_vi": span["text"].strip(),  # Placeholder for Vietnamese translation
                    }
                    cells.append(cell)

                    # Draw bounding box on the page
                    rect = fitz.Rect()
                    page.draw_rect(rect, color=(1, 0, 0), width=0.5)  # Red bounding box with border width = 0.5

    output["cells"] = cells

    # Save the modified PDF with bounding boxes
    output_pdf_path = Path(pdf_path).stem + "_with_bboxes.pdf"
    doc.save(output_pdf_path)
    print(f"PDF with bounding boxes saved to: {output_pdf_path}")

    # Save JSON output if specified
    if output_json_path:
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

    return output

def draw_bounding_boxes_on_pdf(pdf_path, output_pdf_path, bboxes1, bboxes2):
    """
    Draw bounding boxes on a PDF file and save the modified PDF.

    Args:
        pdf_path (str): Path to the input PDF file.
        output_pdf_path (str): Path to save the modified PDF file.
        bboxes (list): List of bounding boxes to draw.
    """
    doc = fitz.open(pdf_path)  # Open the PDF file

    # Draw red bounding boxes (COCO format)\
    for page_num, page in enumerate(doc, start=1):
        for bbox in bboxes1:
            # Create a rectangle from the bounding box
            rect = fitz.Rect(bbox[0], bbox[1], bbox[0] + bbox[2], bbox[1] + bbox[3])
            # Draw the rectangle on the page
            page.draw_rect(rect, color=(1, 0, 0), width=0.5)  # Red bounding box

    # Draw green bounding boxes (original format)
    for page_num, page in enumerate(doc, start=1):
        for bbox in bboxes2:
            # Create a rectangle from the bounding box
            rect = fitz.Rect(bbox[0], bbox[1], bbox[0] + bbox[2], bbox[1] + bbox[3])
            # Draw the rectangle on the page
            page.draw_rect(rect, color=(0, 1, 0), width=0.5)  # Blue bounding box

    # Save the modified PDF
    doc.save(output_pdf_path)
    print(f"PDF with bounding boxes saved to: {output_pdf_path}")

def multiplyList(myList, multiplier):
    for i in range(len(myList)):
        for j in range(len(myList[i])):
            myList[i][j] = myList[i][j] * multiplier

def movedownList(myList, down):
    for i in range(len(myList)):
        myList[i][1] = myList[i][1] * down

def moverightList(myList, right):
    for i in range(len(myList)):
        myList[i][0] = myList[i][0] * right

def main():
    # File paths to the two JSON files
    file1_path = './sample_output.json'  # Path to the first JSON file
    file2_path = './my_output.json'     # Path to the second JSON file

    # Extract bounding boxes from the first JSON file
    file1_bboxes = extract_bboxes_from_json(file1_path)
    file2_bboxes = extract_bboxes_from_json(file2_path)

    # multiplyList(file1_bboxes, 75/130)

    # Input and output PDF paths
    input_pdf_path = "sample_input_coco_standard.pdf"
    output_pdf_path = "sample_input_with_bboxes.pdf"

    # Draw bounding boxes on the PDF
    draw_bounding_boxes_on_pdf(input_pdf_path, output_pdf_path, file1_bboxes, file2_bboxes)


if __name__ == '__main__':
    main()