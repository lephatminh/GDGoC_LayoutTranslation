import csv
import json
import fitz  # PyMuPDF
import ocrmypdf
import os
from pathlib import Path
import time
import logging
from deep_translator import GoogleTranslator
from langdetect import detect, DetectorFactory
from PyPDF2 import PdfReader, PdfWriter, Transformation
import copy


# Add after the other initialization code
DetectorFactory.seed = 0  # For reproducibility


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("ocr_recovery.log"),
        logging.StreamHandler()
    ]
)


def find_max_csv_field_size():
    """Find the maximum CSV field size limit using binary search"""
    max_int = 2147483647  # 2^31-1
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
csv.field_size_limit(find_max_csv_field_size())


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


def apply_ocr_to_pdf(input_path, output_dir):
    """Apply OCR to a PDF file using OCRmyPDF"""
    # Create OCR file in data/test/PDF_ocr directory
    output_path = output_dir / f"{input_path.stem}.ocr.pdf"

    try:
        languages = [
            "chi_sim",  # Simplified Chinese
            "chi_tra",  # Traditional Chinese
            "vie",      # Vietnamese
            "eng",      # English
            "jpn",      # Japanese
            "kor",      # Korean
            "fra",      # French
            "deu",      # German
            "spa",      # Spanish
            "rus"       # Russian
        ]

        # Run OCR with multiple language support
        ocrmypdf.ocr(
            input_path,
            output_path,
            language="+".join(languages),
            deskew=True,
            clean=False,
            optimize=0,
            output_type='pdf',  # Changed from 'pdfa' to 'pdf' to retain original color space
            skip_text=True,
            progress_bar=True,
            color_conversion_strategy='UseDeviceIndependentColor',
        )
        logging.info(f"OCR completed: {output_path}")
        return output_path
    except Exception as e:
        logging.error(f"OCR error: {str(e)}")
        return None


def map_language_code_for_deep_translator(lang_code):
    mapping = {
        "zh-cn": "zh-CN",
        "zh-hans": "zh-CN",
        "zh-tw": "zh-TW",
        'zh-hant': 'zh-TW',
        'zh': 'zh-CN',     # Default Chinese to Simplified
        'jw': 'jv',        # Javanese
        'iw': 'he',        # Hebrew
        'in': 'id',        # Indonesian
        'ceb': 'tl',       # Adjust Cebuano to use Tagalog
    }

    return mapping.get(lang_code, lang_code)


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
                    logging.warning(f"Translation error: {str(e)[:100]}...")
                    # Return original text on error
                    batch_results.append(text)
                    
                    # Handle rate limiting - increase delay and reduce batch size
                    if "429" in str(e) or "too many requests" in str(e).lower():
                        logging.info(f"Rate limit hit. Increasing delay to {delay*2}s and reducing batch size.")
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
                # Map language code for deep_translator
                mapped_lang = map_language_code_for_deep_translator(lang)
                # Store original language in cell
                texts_with_langs.append((cell["text"], mapped_lang, i))
            except Exception as e:
                logging.warning(f"Language detection error: {str(e)[:100]}... Using 'en' as fallback.")
                texts_with_langs.append((cell["text"], "en", i))
    
    logging.info(f"Translating {len(texts_with_langs)} text segments to {target}...")

    lang_counts = {}
    for _, lang, _ in texts_with_langs:
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    
    logging.info("Detected languages:")
    for lang, count in lang_counts.items():
        logging.info(f"  - {lang}: {count} segments")
    
    # Perform batch translation
    translated_texts = batch_translate_text(texts_with_langs, target)
    
    # Map translated texts back to cells
    text_index = 0
    for cell in cells:
        if cell.get("text"):
            cell["text_vi"] = translated_texts[text_index]
            text_index += 1
    
    return cells


def clean_text(text):
    """Clean text by removing/replacing non-printable characters"""
    if not isinstance(text, str):
        return text
        
    # Replace common problematic Unicode characters
    replacements = {
        '\u0000': '',  # NULL
        '\u0001': '',  # START OF HEADING
        '\u0002': '',  # START OF TEXT
        '\u0003': '',  # END OF TEXT
        '\u0004': '',  # END OF TRANSMISSION
        '\u0005': '',  # ENQUIRY
        '\u0006': '',  # ACKNOWLEDGE
        '\u0007': '',  # BELL
        '\u0014': '',  # DEVICE CONTROL FOUR
        '\u0015': '',  # NEGATIVE ACKNOWLEDGE
        '\ufffd': '',  # REPLACEMENT CHARACTER (�)
        '\u200b': '',  # ZERO WIDTH SPACE
        '\u200e': '',  # LEFT-TO-RIGHT MARK
        '\u200f': '',  # RIGHT-TO-LEFT MARK
        '\ufeff': '',  # ZERO WIDTH NO-BREAK SPACE
    }
    
    # Apply replacements
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    
    # Filter out any remaining control characters
    return ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')


def extract_pdf_info(pdf_path):
    """Extract text and formatting information from a PDF file"""
    doc = fitz.open(pdf_path)
    cells = []
    
    try:
        for page_num, page in enumerate(doc, start=1):
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        span["text"] = clean_text(span["text"]).strip()
                        # Skip empty spans
                        if not span["text"]:
                            continue

                        # Normalize text with excessive spacing
                        normalized_text = normalize_spaced_text(span["text"])

                        cell = {
                            "x": span["bbox"][0],
                            "y": span["bbox"][1],
                            "width": span["bbox"][2] - span["bbox"][0],     # width
                            "height": span["bbox"][3] - span["bbox"][1],    # height
                            "text": normalized_text,
                            "font": {
                                "color": int_to_rgb(span["color"]),
                                "name": span["font"],
                                "size": int(span["size"]),
                            },
                            "text_vi": normalized_text  # Will be translated later
                        }
                        cells.append(cell)
    except Exception as e:
        logging.error(f"Error extracting text from {pdf_path}: {str(e)}")
    finally:
        doc.close()
    
    # Add translation step
    if cells:
        try:
            logging.info(f"Translating {len(cells)} cells to Vietnamese...")
            cells = translate_cells(cells, target='vi')
            logging.info(f"Translation complete for {len(cells)} cells")
        except Exception as e:
            logging.error(f"Translation error: {str(e)}")
            # Continue with untranslated text
        
    return {"cells": cells}


# from pdfminer.high_level import extract_pages
# from pdfminer.layout import LTTextContainer, LTChar

# def extract_pdf_info(pdf_path):
#     """Extract text and formatting information using PDFMiner.six"""
#     cells = []
    
#     try:
#         for page_layout in extract_pages(pdf_path):
#             for element in page_layout:
#                 if isinstance(element, LTTextContainer):
#                     for text_line in element:
#                         text = ""
#                         # Default values
#                         x, y, width, height = element.bbox
#                         font_name = ""
#                         font_size = 0
#                         color = [0, 0, 0, 255]  # Default black
                        
#                         # Extract character properties
#                         for character in text_line:
#                             if isinstance(character, LTChar):
#                                 text += character.get_text()
#                                 font_name = character.fontname
#                                 font_size = character.size
#                                 # Some PDFs store color in the character's graphicstate
#                                 if hasattr(character, 'graphicstate') and hasattr(character.graphicstate, 'ncolor'):
#                                     color_values = character.graphicstate.ncolor
#                                     if color_values:
#                                         # Convert RGB values (0-1) to standard RGB (0-255)
#                                         color = [int(c * 255) for c in color_values] + [255]  # Add alpha
                        
#                         if not text.strip():
#                             continue
                            
#                         # normalized_text = normalize_spaced_text(text)
#                         normalized_text = text
                        
#                         cell = {
#                             "x": x,
#                             "y": y,
#                             "width": width - x,
#                             "height": height - y,
#                             "text": normalized_text,
#                             "font": {
#                                 "color": color,
#                                 "name": font_name,
#                                 "size": int(font_size),
#                             },
#                             "text_vi": normalized_text
#                         }
#                         cells.append(cell)
    
#     except Exception as e:
#         logging.error(f"Error extracting text from {pdf_path}: {str(e)}")
    
#     # Add translation
#     if cells:
#         try:
#             cells = translate_cells(cells, target='vi')
#         except Exception as e:
#             logging.error(f"Translation error: {str(e)}")
    
#     return {"cells": cells}


# import pdfplumber

# def extract_pdf_info(pdf_path):
#     """Extract text and formatting using PDFPlumber with color from PyMuPDF"""
#     cells = []
    
#     try:
#         # Open with PDFPlumber for text extraction with positioning
#         with pdfplumber.open(pdf_path) as pdf_plumber:
#             # Also open with PyMuPDF to get color information
#             doc_mupdf = fitz.open(pdf_path)
            
#             for page_num, page in enumerate(pdf_plumber.pages):
#                 # Extract words with positioning from PDFPlumber
#                 words = page.extract_words(
#                     x_tolerance=3,
#                     y_tolerance=3,
#                     keep_blank_chars=True,
#                 )
                
#                 # Get the corresponding PyMuPDF page for color extraction
#                 mupdf_page = doc_mupdf[page_num]
                
#                 for word in words:
#                     if not word["text"].strip():
#                         continue
                    
#                     normalized_text = normalize_spaced_text(word["text"])
                    
#                     # Create a rect for this word to find color in PyMuPDF
#                     rect = fitz.Rect(word["x0"], word["top"], word["x1"], word["bottom"])
                    
#                     # Extract color from PyMuPDF
#                     color = [0, 0, 0, 255]  # Default black
#                     text_blocks = mupdf_page.get_text("dict", clip=rect)
#                     if text_blocks["blocks"]:
#                         for block in text_blocks["blocks"]:
#                             if "lines" in block:
#                                 for line in block["lines"]:
#                                     for span in line["spans"]:
#                                         if span["text"].strip():
#                                             color = int_to_rgb(span["color"])
#                                             break
                    
#                     cell = {
#                         "x": word["x0"],
#                         "y": word["top"],
#                         "width": word["x1"] - word["x0"],
#                         "height": word["bottom"] - word["top"],
#                         "text": normalized_text,
#                         "font": {
#                             "color": color,
#                             "name": word.get("fontname", ""),
#                             "size": float(word.get("size", 0)),
#                         },
#                         "text_vi": normalized_text
#                     }
#                     cells.append(cell)
            
#             # Close PyMuPDF document
#             doc_mupdf.close()
    
#     except Exception as e:
#         logging.error(f"Error extracting text from {pdf_path}: {str(e)}")
    
#     # Add translation
#     if cells:
#         try:
#             cells = translate_cells(cells, target='vi')
#         except Exception as e:
#             logging.error(f"Translation error: {str(e)}")
    
#     return {"cells": cells}


def get_file_ids(file_path):
    """Get expected file IDs from sample submission file"""
    if not file_path.exists():
        logging.warning(f"Sample submission file not found: {file_path}")
        return set()  # Return empty set if file doesn't exist
        
    expected_ids = set()
    try:
        with open(file_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            for row in reader:
                if row and row[0]:  # Check if row exists and has an ID
                    expected_ids.add(row[0])
        
        logging.info(f"Found {len(expected_ids)} expected file IDs")
        return expected_ids
    except Exception as e:
        logging.error(f"Error reading sample submission: {e}")
        return set()


def scale_pdf(input_path, output_path, target_width=1025, target_height=1025):
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


def process_all_pdfs(expected_file_ids, pdf_dir, scaled_dir, ocr_dir, output_csv):
    # Get all pdf files from pdf_dir
    pdf_files = list(pdf_dir.glob("*.pdf"))
    total_files = len(pdf_files)

    # Scale all PDFs to COCO standard size if needed
    scaled_pdf_paths = []
    for i, pdf_file in enumerate(pdf_files, 1):
        # Skip if not in expected_file_ids of sample_submission.csv
        # Only skip if we have expected_file_ids AND the file isn't in it
        if expected_file_ids and pdf_file.stem not in expected_file_ids:
            logging.warning(f"Skipping {pdf_file.name} - not in expected file IDs")
            continue

        output_pdf_path = scaled_dir / f"{pdf_file.stem}.coco_standard.pdf"
        scaled_pdf_paths.append(output_pdf_path)
        
        if not output_pdf_path.exists():
            print(f"[{i}/{total_files}] Scaling: {pdf_file.name}")
            scale_pdf(pdf_file, output_pdf_path)
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
            # Apply OCR to the PDF
            ocr_pdf_file = apply_ocr_to_pdf(scaled_pdf_file, ocr_dir)
            if not ocr_pdf_file:
                logging.error(f"OCR failed for {file_id}")
                continue

            # Process PDF and extract cells
            output = extract_pdf_info(ocr_pdf_file)
            cells = output.get("cells", [])
            
            # Append result to CSV immediately
            with open(output_csv, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
                json_str = json.dumps(cells, ensure_ascii=False)
                json_str = clean_text(json_str)
                writer.writerow([file_id, json_str])
                
            processed_ids.add(file_id)
            print(f"Saved result for {file_id} to {output_csv}")
            
        except Exception as e:
            print(f"Error processing {file_id}: {str(e)}")
            continue

    print(f"Processing complete! {len(processed_ids)} files processed.")


def main():
    # File paths
    sample_file = Path("sample_submission.csv")
    pdf_dir = Path("data/test/PDF")  # Directory with original PDF files
    scaled_dir = Path("data/test/PDF_scaled")
    ocr_dir = Path("data/test/PDF_ocr")
    output_csv = Path("submission_ocr_official.csv")

    # Ensure necessary directories exist
    os.makedirs(pdf_dir, exist_ok=True)
    os.makedirs(scaled_dir, exist_ok=True)
    os.makedirs(ocr_dir, exist_ok= True)

    # Get all valid file ids from sample_file
    all_expected_ids = get_file_ids(sample_file)

    process_all_pdfs(all_expected_ids, pdf_dir, scaled_dir, ocr_dir, output_csv)


if __name__ == "__main__":
    main()