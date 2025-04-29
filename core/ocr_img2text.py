import ocrmypdf
import logging

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
            # skip_text = False,
            # force_ocr = True,
            progress_bar=True,
            color_conversion_strategy='UseDeviceIndependentColor',
        )
        logging.info(f"OCR completed: {output_path}")
        return output_path
    except Exception as e:
        logging.error(f"OCR error: {str(e)}")
        return None