import csv
import json
import fitz  # PyMuPDF
import ocrmypdf
import os
from pathlib import Path
import tempfile
from concurrent.futures import ThreadPoolExecutor
import time
import logging
from deep_translator import GoogleTranslator
from langdetect import detect, DetectorFactory

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

def find_max_csv_field_size():
    """Find the maximum CSV field size limit using binary search"""
    import csv
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

def apply_ocr_to_pdf(input_path, output_path=None, languages=None):
    """Apply OCR to a PDF file using OCRmyPDF"""
    if output_path is None:
        # Create OCR file in data/test/PDF_ocr directory
        output_dir = Path("data/test/PDF_ocr")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / input_path.name

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
            language=languages,
            deskew=True,
            clean=False,
            optimize=0,
            output_type='pdfa',
            skip_text=True,
            progress_bar=True
        )
        logging.info(f"OCR completed: {output_path}")
        return output_path
    except Exception as e:
        logging.error(f"OCR error: {str(e)}")
        return None

def extract_text_from_pdf(pdf_path):
    """Extract text and formatting information from a PDF file"""
    doc = fitz.open(pdf_path)
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

def get_missing_file_ids(sample_file, submission_file):
    """Identify file IDs with missing or empty solutions"""
    # Get all expected file IDs from sample submission
    expected_ids = set()
    with open(sample_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            if row and row[0]:  # Check if row exists and has an ID
                expected_ids.add(row[0])
    
    # Get IDs with valid solutions from current submission
    existing_solutions = {}
    if os.path.exists(submission_file):
        with open(submission_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            for row in reader:
                if len(row) >= 2:
                    file_id = row[0]
                    solution = row[1]
                    # Store the solution if it's not empty
                    if solution.strip() not in ['[]', '""[]""', '{}', '""{}""']:
                        existing_solutions[file_id] = solution
    
    # Find IDs that don't have valid solutions
    missing_ids = expected_ids - set(existing_solutions.keys())
    
    logging.info(f"Found {len(expected_ids)} expected IDs in sample file")
    logging.info(f"Found {len(existing_solutions)} valid solutions in current submission")
    logging.info(f"Need to process {len(missing_ids)} missing file IDs")
    
    return missing_ids, existing_solutions, expected_ids

def process_missing_files(missing_ids, pdf_dir, existing_solutions, output_file):
    """Process files with missing solutions, apply OCR, and extract text"""
    pdf_dir_path = Path(pdf_dir)
    total_missing = len(missing_ids)
    processed = 0
    success = 0
    
    # Track which file IDs we've already written to prevent duplicates
    written_ids = set()

    # Create/verify output file with header if needed
    if not os.path.exists(output_file):
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["id", "solution"])
    
    # Copy existing valid solutions to new file
    with open(output_file, 'w', newline='', encoding='utf-8') as f:  # Changed from 'a' to 'w' to start fresh
        writer = csv.writer(f)
        writer.writerow(["id", "solution"])  # Write header
        
        for file_id, solution in existing_solutions.items():
            if file_id not in written_ids:  # Prevent duplicates
                writer.writerow([file_id, solution])
                written_ids.add(file_id)
    
    logging.info(f"Copied {len(written_ids)} existing solutions to {output_file}")
    
    # Now append new solutions
    with open(output_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Find and process missing files
        for file_id in sorted(missing_ids):
            if file_id in written_ids:  # Skip if already written
                continue
            
            processed += 1
            logging.info(f"Processing {processed}/{total_missing}: {file_id}")
            
            # Find PDF file in directory
            pdf_file = pdf_dir_path / f"{file_id}.coco_standard.pdf"
            if not pdf_file.exists():
                logging.warning(f"PDF file not found: {pdf_file}")
                continue
            
            try:
                # Apply OCR to the PDF
                ocr_path = apply_ocr_to_pdf(pdf_file)
                if not ocr_path:
                    logging.error(f"OCR failed for {file_id}")
                    continue
                    
                # Extract text and translate it
                result = extract_text_from_pdf(ocr_path)
                cells = result.get("cells", [])
                
                if not cells:
                    logging.warning(f"No text extracted from OCR'd PDF: {file_id}")
                    continue
                    
                # Save result to CSV
                writer.writerow([file_id, json.dumps(cells, ensure_ascii=False)])
                written_ids.add(file_id)
                
                success += 1
                logging.info(f"Successfully processed {file_id} with {len(cells)} cells")
                
                # Clean up OCR file if it's a temporary file
                # if ocr_path != pdf_file:
                #     try:
                #         os.unlink(ocr_path)
                #     except:
                #         pass
                    
            except Exception as e:
                logging.error(f"Error processing {file_id}: {str(e)}")
    
    return success, total_missing

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

def map_language_code_for_deep_translator(lang_code):
    mapping = {
        "zh-cn": "zh-CN",
        "zh-tw": "zh-TW",
        'zh': 'zh-CN',     # Default Chinese to Simplified
        'jw': 'jv',        # Javanese
        'iw': 'he',        # Hebrew
        'in': 'id',        # Indonesian
        'ceb': 'tl',       # Adjust Cebuano to use Tagalog
    }

    return mapping.get(lang_code, lang_code)

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

def main():
    # File paths
    sample_file = "sample_submission.csv"
    current_submission = "submission.csv"
    new_submission = "submission_fill.csv"
    pdf_dir = "data/test/PDF_scaled"  # Directory with original PDF files
    
    # Ensure necessary directories exist
    os.makedirs(pdf_dir, exist_ok=True)
    
    # Get missing file IDs
    missing_ids, existing_solutions, all_expected_ids = get_missing_file_ids(
        sample_file, current_submission)
    
    if not missing_ids:
        logging.info("No missing solutions found. All files have valid solutions!")
        return
    
    # Process missing files
    success, total = process_missing_files(
        missing_ids, pdf_dir, existing_solutions, new_submission)
    
    # Log summary
    logging.info(f"Processing complete!")
    logging.info(f"Successfully processed {success}/{total} missing files")
    logging.info(f"New submission file created: {new_submission}")
    
    # Verify final submission content
    try:
        with open(new_submission, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            final_count = sum(1 for _ in reader)
            
        coverage = (final_count / len(all_expected_ids)) * 100
        logging.info(f"Final submission contains {final_count}/{len(all_expected_ids)} "
                     f"entries ({coverage:.2f}% coverage)")
    except Exception as e:
        logging.error(f"Error verifying final submission: {str(e)}")

if __name__ == "__main__":
    main()