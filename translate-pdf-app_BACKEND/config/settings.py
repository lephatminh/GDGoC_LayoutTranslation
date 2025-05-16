import os
from pathlib import Path

# Directory Structure
BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = BASE_DIR / "data"
TEST_DIR = BASE_DIR / "test"
STORE_DIR = BASE_DIR / "store"
TEST_PDF_DIR = TEST_DIR / "PDF"
TEST_SCALED_DIR = TEST_DIR / "PDF_scaled"
TEST_OCR_DIR = TEST_DIR / "PDF_ocr"

# Files
SAMPLE_SUBMISSION = BASE_DIR / "sample_submission.csv"
OUTPUT_CSV = BASE_DIR / "submission.csv"
SUBMISSION_PARTS = [
    BASE_DIR / "submission_ocr_official_part_1.csv",
    BASE_DIR / "submission_ocr_official_part_2.csv",
    BASE_DIR / "submission_ocr_official_part_3.csv",
    BASE_DIR / "submission_ocr_official_part_4.csv"
]

# PDF processing settings
TARGET_WIDTH = 1025
TARGET_HEIGHT = 1025

# Logging
LOG_FILE = BASE_DIR / "ocr_recovery.log"