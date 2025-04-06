import ocrmypdf
import fitz  # PyMuPDF
import json
import csv
import os
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter, Transformation
import copy
from deep_translator import GoogleTranslator
import time
from langdetect import detect, DetectorFactory

# Find the maximum CSV field size limit using binary search
def find_max_csv_field_size():
    max_int = 2147483647  # 2^31-1 (max signed 32-bit integer)
    min_int = 1024
    
    while min_int < max_int:
        try:
            mid = (min_int + max_int + 1) // 2
            csv.field_size_limit(mid)
            min_int = mid
        except OverflowError:
            max_int = mid - 1
    
    return min_int

# Safely set maximum CSV field size limit
max_csv_field_size = find_max_csv_field_size()
csv.field_size_limit(max_csv_field_size)
DetectorFactory.seed = 0  # For reproducibility

def apply_ocr_to_pdf(input_path, output_path=None):
    """
    Apply OCR to a PDF file using OCRmyPDF.
    Returns path to the OCR'd PDF.
    """
    if output_path is None:
        # Create output in same location as input with "_ocr" suffix
        input_path = Path(input_path)
        output_path = input_path.parent / f"{input_path.stem}_ocr{input_path.suffix}"
    
    try:
        # Run OCR with multiple language support
        ocrmypdf.ocr(
            input_path, 
            output_path,
            deskew=True,              # Straighten text
            clean=False,              # Don't remove image artifacts
            optimize=0,               # No optimization to preserve quality
            output_type='pdfa',
            skip_text=True,           # Process even if text is present
            progress_bar=True         # Show progress
        )
        print(f"OCR completed: {output_path}")
        return output_path
    except Exception as e:
        print(f"OCR error: {str(e)}")
        # If OCR fails, return the original file
        return input_path

def batch_translate_text(texts_with_langs, target='vi', batch_size=25, delay=0):
    """
    Translate a batch of texts with rate limiting.
    
    Args:
        texts: List of texts to translate
        source: Source language code
        target: Target language code
        batch_size: Number of texts to translate in one batch
        delay: Delay between batches in seconds
        
    Returns:
        List of translated texts
    """
    results = [""] * len(texts_with_langs)

    # Group text by detected source language
    lang_groups = {}
    for text, lang, orig_idx in texts_with_langs:
        if not lang in lang_groups:
            lang_groups[lang] = []
        lang_groups[lang].append((text, orig_idx))

    for source_lang, texts_with_indices in lang_groups.items():
        if source_lang == target:
            for text, orig_idx in texts_with_indices:
                results[orig_idx] = text
            continue

        texts = [t[0] for t in texts_with_indices]
        indices = [t[1] for t in texts_with_indices]

        # Create translator for this language
        translator = GoogleTranslator(source=source_lang, target=target)

        translated_batch = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:min(i + batch_size, len(texts))]
            
            # Process each text in the current batch
            batch_results = []
            for text in batch:
                try:    
                    translated = translator.translate(text)
                    batch_results.append(translated)
                    
                except Exception as e:
                    print(f"Translation error: {str(e)[:100]}...")
                    # Return original text on error
                    batch_results.append(text)
                    
                    # Handle rate limiting - increase delay and reduce batch size
                    if "429" in str(e) or "too many requests" in str(e).lower():
                        print(f"Rate limit hit. Increasing delay to {delay*2}s and reducing batch size.")
                        delay *= 2
                        batch_size = max(1, batch_size // 2)
                        time.sleep(5)  # Additional pause after hitting rate limit
            
            translated_batch.extend(batch_results)
            
            # Add delay between batches
            if i + batch_size < len(texts):
                time.sleep(delay)

        # Put translated texts back in their original positions
        for translated_text, orig_idx in zip(translated_batch, indices):
            results[orig_idx] = translated_text
            
    return results

def translate_cells(cells, target='vi'):
    """
    Translate text in cells from source language to target language.
    
    Args:
        cells: List of cell dictionaries with text
        source: Source language code
        target: Target language code
        
    Returns:
        List of cell dictionaries with translated text
    """
    # Extract all texts and detect languages
    texts_with_langs = []
    for i, cell in enumerate(cells):
        if cell.get("text"):
            try:
                # Detect language for each text
                lang = detect(cell["text"])
                # Store original language in cell
                texts_with_langs.append((cell["text"], lang, i))
            except Exception as e:
                print(f"Language detection error: {str(e)[:100]}... Using 'en' as fallback.")
                texts_with_langs.append((cell["text"], "en", i))
    
    print(f"Translating {len(texts_with_langs)} text segments to {target}...")

    lang_counts = {}
    for _, lang, _ in texts_with_langs:
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    
    print("Detected languages:")
    for lang, count in lang_counts.items():
        print(f"  - {lang}: {count} segments")
    
    # Perform batch translation
    translated_texts = batch_translate_text(texts_with_langs, target)
    
    # Map translated texts back to cells
    text_index = 0
    for cell in cells:
        if cell.get("text"):
            cell["text_vi"] = translated_texts[text_index]
            text_index += 1
    
    return cells

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

def normalize_spaced_text(text):
    """
    Normalize text with excessive spacing between characters,
    commonly found in headers like "F I N A N C I A L  S T A T E M E N T S" or ""
    """
    # Check if text has consistent spacing pattern (every character followed by space)
    if len(text) > 3 and all(text[i] == ' ' for i in range(1, len(text), 2)):
        # Join characters by removing spaces
        return ''.join(text[i] for i in range(0, len(text), 2))
    
    # Check if text has spaces between all characters
    if len(text) > 3 and ' ' in text:
        # Count spaces vs non-spaces
        spaces = text.count(' ')
        non_spaces = len(text) - spaces
        
        # If the ratio of spaces to characters is high (e.g., spaces >= characters)
        if spaces >= non_spaces - 1:
            text_split = text.split(' ')
            text_split = [' ' if char == '' else char for char in text_split]
            return ''.join(text_split)
    
    # Return original if no patterns match
    return text

def extract_pdf_info(pdf_path, output_json_path=None):
    doc = fitz.open(pdf_path)
    output = {}
    
    # Extract text cells
    cells = []
    try:
        for page_num, page in enumerate(doc, start=1):
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        span["text"] = span["text"].strip()
                        # Skip empty spans
                        if not span["text"]:
                            continue

                        # Normalize text with excessive spacing
                        normalized_text = normalize_spaced_text(span["text"])

                        cell = {
                            "bbox": [
                                span["bbox"][0], 
                                span["bbox"][1],
                                span["bbox"][2] - span["bbox"][0],  # width
                                span["bbox"][3] - span["bbox"][1]   # height
                            ],
                            "text": normalized_text,
                            "font": {
                                "color": int_to_rgb(span["color"]),
                                "name": span["font"],
                                "size": int(span["size"]),  # Normalized size
                            },
                            "text_vi": normalized_text  # Placeholder for Vietnamese translation
                        }

                        cells.append(cell)
    finally:
        doc.close()

    if not cells:
        print("No text cells found in the PDF.")
        ocr_path = apply_ocr_to_pdf(pdf_path)
        if ocr_path and ocr_path != pdf_path:
            doc = fitz.open(ocr_path)
            try:
                for page_num, page in enumerate(doc, start=1):
                    blocks = page.get_text("dict")["blocks"]
                    for block in blocks:
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                span["text"] = span["text"].strip()
                                if not span["text"]:
                                    continue
                                
                                normalized_text = normalize_spaced_text(span["text"])
                                
                                cell = {
                                    "bbox": [
                                        span["bbox"][0], 
                                        span["bbox"][1],
                                        span["bbox"][2] - span["bbox"][0], 
                                        span["bbox"][3] - span["bbox"][1]
                                    ],
                                    "text": normalized_text,
                                    "font": {
                                        "color": int_to_rgb(span["color"]),
                                        "name": span["font"],
                                        "size": int(span["size"]), 
                                    },
                                    "text_vi": normalized_text
                                }
                                cells.append(cell)
            finally:
                doc.close()
                
            print(f"OCR extraction found {len(cells)} cells")

    # Translate text if requested
    if cells:
        try:
            print(f"Translating {len(cells)} cells...")
            cells = translate_cells(cells, target='vi')
            print(f"Translation complete for {len(cells)} cells")
        except Exception as e:
            print(f"Translation error: {e}")
            # Continue with untranslated text
    
    output["cells"] = cells

    if output_json_path:
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

    return output

def scale_pdf_properly(input_path, output_path, target_width=1025, target_height=1025):
    """
    Scale a PDF to the target dimensions ensuring both page size and content are scaled.

    Args:
        input_path (str): Path to the input PDF file
        output_path (str): Path where the scaled PDF will be saved
        target_width (int): Target width in pixels (default: 1025)
        target_height (int): Target height in pixels (default: 1025)
    """
    # Read the original PDF
    reader = PdfReader(input_path)
    writer = PdfWriter()

    # Convert target dimensions from pixels to points (72 points = 1 inch)
    # Assuming 72 DPI resolution
    target_width_pts = target_width
    target_height_pts = target_height

    # Process each page
    for page_num in range(len(reader.pages)):
        # Get the original page
        original_page = reader.pages[page_num]

        # Get original page dimensions
        mediabox = original_page.mediabox
        orig_width = float(mediabox.width)
        orig_height = float(mediabox.height)

        # Calculate scaling factors
        width_scale = target_width_pts / orig_width
        height_scale = target_height_pts / orig_height

        # Create a copy of the page to work with
        page = copy.deepcopy(original_page)

        # Apply scaling transformation to the content
        transform = Transformation().scale(width_scale, height_scale)
        page.add_transformation(transform)

        # Update the mediabox to the new dimensions
        # PyPDF2 uses a coordinate system with (0,0) at the bottom left
        page.mediabox.lower_left = (0, 0)
        page.mediabox.upper_right = (target_width_pts, target_height_pts)

        # Also update cropbox and trimbox if they exist
        if "/CropBox" in page:
            page.cropbox.lower_left = (0, 0)
            page.cropbox.upper_right = (target_width_pts, target_height_pts)

        if "/TrimBox" in page:
            page.trimbox.lower_left = (0, 0)
            page.trimbox.upper_right = (target_width_pts, target_height_pts)

        if "/ArtBox" in page:
            page.artbox.lower_left = (0, 0)
            page.artbox.upper_right = (target_width_pts, target_height_pts)

        if "/BleedBox" in page:
            page.bleedbox.lower_left = (0, 0)
            page.bleedbox.upper_right = (target_width_pts, target_height_pts)

        # Add the scaled page to the output PDF
        writer.add_page(page)

    # Write the result to the output file
    with open(output_path, "wb") as output_file:
        writer.write(output_file)

    print(f"PDF scaled successfully to {target_width}x{target_height}.")
    print(f"Both page dimensions and content have been scaled. Saved to {output_path}")

def process_all_pdfs():
    pdf_dir = Path("data/test/PDF_ocr")
    scaled_dir = Path("data/test/PDF_scaled")
    output_csv = Path("submission_test.csv")

    os.makedirs(pdf_dir, exist_ok=True)
    os.makedirs(scaled_dir, exist_ok=True)

    pdf_files = list(pdf_dir.glob("*.pdf"))
    total_files = len(pdf_files)

    # Scale all PDFs to COCO standard size if needed
    scaled_pdf_paths = []
    for i, pdf_file in enumerate(pdf_files, 1):
        output_pdf_path = scaled_dir / f"{pdf_file.stem}.coco_standard.pdf"
        scaled_pdf_paths.append(output_pdf_path)
        
        if not output_pdf_path.exists():
            print(f"[{i}/{total_files}] Scaling: {pdf_file.name}")
            scale_pdf_properly(pdf_file, output_pdf_path)
        else:
            print(f"[{i}/{total_files}] Already scaled: {pdf_file.name}")

    # Create CSV file with header if it doesn't exist
    csv_exists = output_csv.exists()
    if not csv_exists:
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "solution"])
    
    # Keep track of already processed files
    processed_ids = set()
    if csv_exists:
        with open(output_csv, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            # Check if the file has any rows before trying to skip the header
            try:
                next(reader)  # Skip header
                for row in reader:
                    if row:
                        processed_ids.add(row[0])
                print(f"Found {len(processed_ids)} already processed files in submission.csv")
            except StopIteration:
                # File exists but is empty or only contains header
                print("Existing submission.csv appears to be empty. Starting fresh.")
                # Reset the file with just a header
                with open(output_csv, "w", newline="", encoding="utf-8") as f_reset:
                    writer = csv.writer(f_reset)
                    writer.writerow(["id", "solution"])
        print(f"Found {len(processed_ids)} already processed files in submission.csv")

    # Process each PDF and append to CSV immediately
    for idx, scaled_pdf_file in enumerate(scaled_pdf_paths, 1):
        # Extract file ID from filename
        file_id = scaled_pdf_file.stem.replace(".coco_standard", "")
        
        # Skip if already processed
        if file_id in processed_ids:
            print(f"[{idx}/{total_files}] Skipping already processed: {file_id}")
            continue
            
        print(f"[{idx}/{total_files}] Processing: {scaled_pdf_file.name}")
        
        try:
            # Process PDF and extract cells
            output = extract_pdf_info(scaled_pdf_file)
            cells = output.get("cells", [])
            
            # Append result to CSV immediately
            with open(output_csv, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, quoting=csv.QUOTE_ALL)
                writer.writerow([file_id, json.dumps(cells, ensure_ascii=False)])
                
            processed_ids.add(file_id)
            print(f"Saved result for {file_id} to {output_csv}")
            
        except Exception as e:
            print(f"Error processing {file_id}: {str(e)}")
            continue

    print(f"Processing complete! {len(processed_ids)} files processed.")

if __name__ == "__main__":
    process_all_pdfs()