import fitz  # PyMuPDF
import json
from pathlib import Path

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

def extract_pdf_info(pdf_path, output_json_path=None):
    doc = fitz.open(pdf_path)
    output = {}
    
    # Extract text cells
    cells = []
    for page_num, page in enumerate(doc, start=1):
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    cell = {
                        "bbox": [
                            span["bbox"][0], 
                            span["bbox"][1],
                            span["bbox"][2] - span["bbox"][0],  # width
                            span["bbox"][3] - span["bbox"][1]   # height
                        ],
                        "text": span["text"].strip(),
                        "font": {
                            "color": int_to_rgb(span["color"]),
                            "name": span["font"],
                            "size": 1  # Normalized size
                        },
                        "text_vi": span["text"].strip()  # Placeholder for Vietnamese translation
                    }

                    if (cell["text"]): 
                        cells.append(cell)

    output["cells"] = cells

    if output_json_path:
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

    return output

# Example usage
pdf_file = "sample_input.pdf"
output_json = "my_output.json"
result = extract_pdf_info(pdf_file, output_json)