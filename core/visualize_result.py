import fitz
import os
import shutil
import tempfile
import logging


def translation_text_visualization(cells ,pdf_path, font_file_path="Roboto.ttf"):
    """
    Extract text from a PDF using OCR, save to CSV, and visualize text in a new PDF.
    
    Args:
        cells: 
            [{'x', 'y', 'width', 'height', 'text', ... 'text_vi'}, ...]
        pdf_path (str): Path to the input PDF file.
        font_file_path (str): Path to the custom font file (default: './Roboto.ttf').
    """

    doc = fitz.open(pdf_path)
    page = doc[0]

    output_pdf_path = 'translation_' + pdf_path

    data = cells

    for entry in data:
        x = entry["x"]
        y = entry["y"]
        width = entry["width"]
        height = entry["height"]
        text = entry["text"]  # Placeholder "original" from extract_pdf_cells
        text_vi = entry["text_vi"]  # Placeholder "vietnamese" from extract_pdf_cells
        # Optionally use original text if visualization requires it
        # text_vi = entry["text"]  # Uncomment to use original text instead
        font_size = entry["font"]["size"]
        font_name = 'Roboto'
        
        #text_vi = '= 3, có khả năng vật chất Hagedorn trực giao trải qua bậc ba'

        # width = text_visual_length(text) # No,we are override, this rectangele will smaller than the initial word

        # Define the rectangle for the text
        rect = fitz.Rect(x, y, x + width, y + height)

        # Cover the original text with a white rectangle
        #page.draw_rect(rect, color=[1, 1, 1], fill=[1, 1, 1])
        page.draw_rect(rect, color=[0, 0, 0], fill=[1, 1, 1])

        # Initialize the font object from file
        font = fitz.Font(fontname=font_name, fontfile=font_file_path)

        font_size = 20

        # Measure and shrink font to fit the box
        text_width = font.text_length(text_vi, fontsize=font_size)
        #print(text,':',text_width)
        while text_width > width and font_size > 1:
                font_size -= 1
                text_width = font.text_length(text_vi, fontsize=font_size)

        # Center the text vertically in the rectangle
        y_text_pos = y  + (height)

        # Insert the text
        page.insert_text(
            (x, y_text_pos),
            text_vi,
            fontsize=font_size,
            fontname=font_name,
            fontfile=font_file_path,
            encoding='utf-16',
            fill_opacity=1,
            stroke_opacity=1,
            border_width=1
        )
        logging.info(f"Visualized text at ({x}, {y}) with '{text}'")

    # Step 6: Save the modified PDF
    try:

        doc.save(output_pdf_path)
        doc.close()
        logging.info(f"PDF modified and saved as {output_pdf_path}")
    except Exception as e:
        logging.error(f"Error saving PDF: {str(e)}")
        doc.close()
        return
    

def visualize_translation(original_pdf, translated_boxes, math_boxes, output_path, font_file_path="Roboto.ttf"):
    """
    Create a visualization of translated text and math notation boxes in a PDF
    
    Args:
        original_pdf: Path to the original PDF file
        translated_boxes: List of text boxes with translations
        math_boxes: List of math notation boxes
        output_path: Path to save the output PDF
        font_file_path: Path to the font file for visualizing translations
    """
    # Create a temporary working folder
    with tempfile.TemporaryDirectory() as working_folder:
        # Copy the original PDF to the working folder
        file_id = os.path.splitext(os.path.basename(original_pdf))[0]
        temp_pdf_path = os.path.join(working_folder, os.path.basename(original_pdf))
        shutil.copy(original_pdf, temp_pdf_path)
        
        # Open the PDF for modification
        doc = fitz.open(temp_pdf_path)
        
        # Process each page (expand document if needed based on max page in boxes)
        max_page = 1
        for box in translated_boxes:
            if box.get("page", 1) > max_page:
                max_page = box.get("page", 1)
        
        # Ensure document has enough pages
        while len(doc) < max_page:
            doc.insert_page(len(doc))
        
        # Group boxes by page
        boxes_by_page = {}
        for box in translated_boxes:
            page_num = box.get("page", 1)
            if page_num not in boxes_by_page:
                boxes_by_page[page_num] = []
            boxes_by_page[page_num].append(box)
        
        # Group math boxes by page
        math_by_page = {}
        for box in math_boxes:
            page_num = box.get("page", 1)
            if page_num not in math_by_page:
                math_by_page[page_num] = []
            math_by_page[page_num].append(box)
        
        # Process each page
        for page_num in range(1, max_page + 1):
            page_idx = page_num - 1  # Convert to 0-based index
            if page_idx >= len(doc):
                continue
                
            page = doc[page_idx]
            
            # First insert math boxes (so text appears above them)
            if page_num in math_by_page:
                for math_box in math_by_page[page_num]:
                    x = math_box["x"]
                    y = math_box["y"]
                    width = math_box["width"]
                    height = math_box["height"]
                    
                    # Define rectangle for math box
                    rect = fitz.Rect(x, y, x + width, y + height)
                    
                    # Try to find corresponding image
                    box_id = math_box.get("box_id", "")
                    img_paths = [
                        os.path.join("YOLO_Math_detection", file_id, "images", f"{box_id}.jpg"),
                        os.path.join("YOLO_Math_detection", file_id, "images", f"{int(float(box_id))}.jpg"),
                    ]
                    
                    img_found = False
                    for img_path in img_paths:
                        if os.path.exists(img_path):
                            try:
                                # Insert the math image
                                page.insert_image(rect, filename=img_path)
                                img_found = True
                                break
                            except Exception as e:
                                print(f"Error inserting image {img_path}: {e}")
                    
                    # If no image found, draw a yellow highlight box
                    if not img_found:
                        # Use a light yellow highlight for math areas
                        page.draw_rect(rect, color=(1, 0.8, 0), fill=(1, 0.9, 0, 0.3), width=0.5)
            
            # Then insert translated text
            if page_num in boxes_by_page:
                for box in boxes_by_page[page_num]:
                    x = box["x"]
                    y = box["y"]
                    width = box["width"]
                    height = box["height"]
                    text = box.get("text", "").strip()
                    text_vi = box.get("text_vi", text).strip()
                    
                    # Skip math boxes that might have been included
                    is_math_box = False
                    for math_box in math_boxes:
                        if (math_box.get("page", 1) == page_num and
                            abs(math_box["x"] - x) < 5 and
                            abs(math_box["y"] - y) < 5 and
                            abs(math_box["width"] - width) < 5 and
                            abs(math_box["height"] - height) < 5):
                            is_math_box = True
                            break
                    
                    if is_math_box:
                        continue
                        
                    # Define the rectangle for the text
                    rect = fitz.Rect(x, y, x + width, y + height)
                    
                    # Cover the original text with a white rectangle with black border
                    page.draw_rect(rect, color=(0, 0, 0), fill=(1, 1, 1), width=0.5)
                    
                    try:
                        # Convert font_file_path to string if it's a Path object
                        if hasattr(font_file_path, "as_posix"):
                            font_file_path = font_file_path.as_posix()
                        
                        # Start with a reasonable font size
                        font_size = min(20, height * 0.8)
                        
                        # Measure and shrink font to fit the box
                        # Instead of creating a separate Font object, we'll use the text width calculation method
                        # available directly on the page
                        text_width = page.text_length(text_vi, fontsize=font_size, fontname="Roboto", fontfile=font_file_path)
                        while text_width > width * 0.95 and font_size > 6:
                            font_size -= 1
                            text_width = page.text_length(text_vi, fontsize=font_size, fontname="Roboto", fontfile=font_file_path)
                        
                        # Position text at the baseline (adjusting for Vietnamese diacritics)
                        y_text_pos = y + height * 0.8
                        
                        # Instead of creating a Font object, directly use insert_text with fontfile parameter
                        page.insert_text(
                            (x + 2, y_text_pos),  # Small horizontal offset for padding
                            text_vi,
                            fontsize=font_size,
                            fontname="Roboto",
                            fontfile=font_file_path,  # Pass the string path directly
                            color=(0, 0, 0)
                        )
                    except Exception as e:
                        print(f"Error inserting text: {e}")
                        # Fallback method using built-in fonts if custom font fails
                        try:
                            # Try with Roboto but without fontfile parameter
                            page.insert_text(
                                (x + 2, y_text_pos),
                                text_vi,
                                fontsize=font_size,
                                fontname="Roboto",
                                color=(0, 0, 0)
                            )
                        except Exception as e2:
                            print(f"Fallback text insertion also failed: {e2}")
        
        # Add legend to the first page
        page = doc[0]
        y_pos = 20  # Starting Y position
        
        # Convert font_file_path to string for legend too
        if hasattr(font_file_path, "as_posix"):
            font_file_path = font_file_path.as_posix()
            
        try:
            # Add a title
            page.insert_text((20, y_pos), "Translation Legend:", fontsize=12, fontname="Roboto", fontfile=font_file_path)
            y_pos += 20
            
            # Legend for translated text
            page.draw_rect(fitz.Rect(20, y_pos, 40, y_pos + 10), color=(0, 0, 0), fill=(1, 1, 1))
            page.insert_text((45, y_pos + 8), "Translated text", fontsize=10, fontname="Roboto", fontfile=font_file_path)
            y_pos += 20
            
            # Legend for math notation
            page.draw_rect(fitz.Rect(20, y_pos, 40, y_pos + 10), color=(1, 0.8, 0), fill=(1, 0.9, 0, 0.3))
            page.insert_text((45, y_pos + 8), "Math notation (preserved)", fontsize=10, fontname="Roboto", fontfile=font_file_path)
        except Exception as e:
            print(f"Error adding legend: {e}")
        
        # Save the modified PDF
        doc.save(output_path)
        doc.close()
        
    return output_path