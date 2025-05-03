import os
import json
import clr
import System
from pathlib import Path
import logging
import csv
from typing import List, Dict, Any, Tuple

# Get the directory where the script is located
script_dir = Path(os.path.dirname(os.path.abspath(__file__)))

# Add the bin directory to the path
bin_dir = script_dir / "bin"

# Add references to PDFPig assemblies with full paths
clr.AddReference(str(bin_dir / "UglyToad.PdfPig.dll"))
clr.AddReference(str(bin_dir / "UglyToad.PdfPig.DocumentLayoutAnalysis.dll"))

# Import the required classes
from UglyToad.PdfPig import PdfDocument
from UglyToad.PdfPig.DocumentLayoutAnalysis import PageSegmenter
from UglyToad.PdfPig.DocumentLayoutAnalysis.WordExtractor import NearestNeighbourWordExtractor

# Try different ReadingOrder import approaches
try:
    # Try importing from different possible namespaces
    from UglyToad.PdfPig.DocumentLayoutAnalysis.ReadingOrder import ReadingOrder
except ImportError:
    try:
        from UglyToad.PdfPig.DocumentLayoutAnalysis import ReadingOrder
    except ImportError:
        try:
            from UglyToad.PdfPig.DocumentLayoutAnalysis.ReadingOrderDetector import ReadingOrderDetector as ReadingOrder
        except ImportError:
            # Define a simple placeholder if the class can't be found
            class ReadingOrder:
                @staticmethod
                def Get(blocks):
                    return blocks  # Just return blocks as-is

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("pdfpig_extraction.log"),
        logging.StreamHandler()
    ]
)

def extract_pdf_layout(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Extract text with layout information from a PDF using PDFPig,
    which can identify paragraphs rather than just individual lines.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        List of cell dictionaries containing text and positioning information
    """
    cells = []
    
    try:
        # Try to open the PDF file - handle the context manager error
        try:
            document = PdfDocument.Open(str(pdf_path))
        except Exception as open_err:
            logging.error(f"Failed to open PDF with PDFPig: {open_err}")
            return cells
            
        # Process each page
        # Fixed: Use document.NumberOfPages instead of GetNumberOfPages
        for page_num in range(document.NumberOfPages):
            try:
                # Get the page (1-based index)
                # Fixed: Use document.GetPage directly
                page = document.GetPage(page_num + 1)
                logging.info(f"Processing page {page_num + 1} of {document.NumberOfPages}")
                
                # Extract words using nearest neighbor algorithm
                word_extractor = NearestNeighbourWordExtractor()
                words = word_extractor.GetWords(page.Letters)
                
                # Use page segmenter to identify paragraphs and text blocks
                try:
                    # Try the static method first (newer versions)
                    text_blocks = PageSegmenter.GetBlocks(words)
                except Exception as block_err:
                    logging.warning(f"Static PageSegmenter.GetBlocks failed: {block_err}")
                    try:
                        # Try instantiating PageSegmenter first (older versions)
                        segmenter = PageSegmenter()
                        text_blocks = segmenter.GetBlocks(words)
                    except Exception as block_err2:
                        logging.warning(f"Instance PageSegmenter.GetBlocks failed: {block_err2}")
                        # Last resort: just treat each word as a separate block
                        text_blocks = [words]
                
                # Try different approach for reading order based on your PDFPig version
                try:
                    # Method 1: Using ReadingOrder class (newer versions)
                    ordered_blocks = ReadingOrder.Get(text_blocks)
                except Exception as e:
                    logging.warning(f"Could not use ReadingOrder.Get: {e}")
                    # Method 2: Just use blocks directly if reading order isn't available
                    ordered_blocks = text_blocks
                
                for block_idx, block in enumerate(ordered_blocks):
                    # Get text from the block (paragraph)
                    try:
                        block_text = " ".join([word.Text for word in block.GetWords()])
                    except AttributeError:
                        # If block doesn't have GetWords method, try alternative
                        try:
                            block_text = block.Text
                        except:
                            block_text = "Unable to extract text"
                    
                    # Get bounding box of the block
                    try:
                        bounds = block.BoundingBox
                        x = bounds.Left
                        y = bounds.Bottom
                        width = bounds.Width
                        height = bounds.Height
                    except AttributeError:
                        # Fallback if BoundingBox not available
                        logging.warning("Could not access BoundingBox, using default values")
                        x, y, width, height = 0, 0, 0, 0
                    
                    # Create a cell entry similar to your current pipeline format
                    cell = {
                        "x": x,
                        "y": y,
                        "width": width,
                        "height": height,
                        "text": block_text.strip(),
                        "block_type": "paragraph",  # Identify this as a paragraph block
                        "page": page_num + 1,
                        "block_index": block_idx
                    }
                    
                    # Try to extract font information if available
                    try:
                        if hasattr(block, "GetWords") and len(block.GetWords()) > 0 and len(block.GetWords()[0].Letters) > 0:
                            first_letter = block.GetWords()[0].Letters[0]
                            if hasattr(first_letter, "FontName") and first_letter.FontName:
                                cell["font"] = {
                                    "name": first_letter.FontName,
                                    "size": first_letter.PointSize
                                }
                                
                                # Try to get color (not always available in PDFPig)
                                if hasattr(first_letter, "Color") and first_letter.Color:
                                    rgb = first_letter.Color
                                    cell["font"]["color"] = [rgb.R, rgb.G, rgb.B]
                    except Exception as font_err:
                        logging.warning(f"Could not extract font info: {font_err}")
                    
                    cells.append(cell)
                    
            except Exception as page_err:
                logging.error(f"Error processing page {page_num + 1}: {page_err}")
                continue
        
        # Properly dispose the document
        document.Dispose()
    
    except Exception as e:
        logging.error(f"Error processing PDF {pdf_path}: {str(e)}")
    
    return cells

def process_pdfs_with_pdfpig(pdf_dir: Path, output_csv: Path):
    """
    Process all PDFs in a directory using PDFPig and save results to CSV
    
    Args:
        pdf_dir: Directory containing PDF files
        output_csv: Path to output CSV file
    """
    # Get all PDF files
    pdf_files = list(pdf_dir.glob("*.pdf"))
    total_files = len(pdf_files)
    
    # Create CSV file with header
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "solution"])
    
    # Process each PDF
    for idx, pdf_file in enumerate(pdf_files, 1):
        file_id = pdf_file.stem
        logging.info(f"[{idx}/{total_files}] Processing: {file_id}")
        
        try:
            # Extract layout information
            cells = extract_pdf_layout(pdf_file)
            
            # Save to CSV
            with open(output_csv, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                json_str = json.dumps(cells, ensure_ascii=False)
                writer.writerow([file_id, json_str])
                
            logging.info(f"Saved result for {file_id} with {len(cells)} blocks")
            
        except Exception as e:
            logging.error(f"Error processing {file_id}: {str(e)}")
    
    logging.info(f"Processing complete! {total_files} files processed.")

def main():
    # File paths
    pdf_dir = Path("data/test/PDF")  # Use your scaled PDFs
    output_csv = Path("submission_pdfpig.csv")
    
    # Ensure necessary directories exist
    os.makedirs(pdf_dir, exist_ok=True)
    
    # Process PDFs
    process_pdfs_with_pdfpig(pdf_dir, output_csv)

if __name__ == "__main__":
    main()