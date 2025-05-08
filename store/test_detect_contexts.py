# A script to test extract contexts by outputing corresponding contexts for each pymupdf bounding boxes

import json
import csv
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import random
from core.extract_contexts import get_contexts, get_all_contexts
import fitz  # PyMuPDF
import pandas as pd

def load_csv_data_pdfpig(csv_path):
    """Load the submission CSV file with extracted boxes"""
    results = {}
    
    # Read the file directly and process one line at a time
    with open(csv_path, 'r', encoding='utf-8') as f:
        # Skip header
        next(f)
        
        for line in f:
            # Find the first comma that separates id from JSON
            first_comma_pos = line.find(',')
            if (first_comma_pos > 0):
                file_id = line[:first_comma_pos].strip()
                json_data = line[first_comma_pos+1:].strip()
                
                # Skip empty rows
                if not file_id:
                    continue
                
                try:
                    # Try direct JSON parsing
                    boxes = json.loads(json_data)
                    results[file_id] = boxes
                    print(f"Successfully parsed data for {file_id}")
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON for {file_id}: {e}")
    
    return results


def load_csv_data_pymupdf(csv_path):
    """Load the submission CSV file with extracted boxes"""
    results = {}
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Skip header
            header = f.readline()
            
            for line in f:
                # Find the first real comma that separates id from solution
                # The challenge here is that there's a comma after "id" in the header
                parts = line.split(',', 1)  # Split only on the first comma
                    
                file_id = parts[0].strip()
                json_data = parts[1].strip()
                
                # Remove any leading/trailing quotes if present
                if json_data.startswith('"') and json_data.endswith('"'):
                    json_data = json_data[1:-1]
                
                # Replace escaped quotes with regular quotes
                json_data = json_data.replace('\\"', '"')
                json_data = json_data.replace('""', '"')
                
                try:
                    boxes = json.loads(json_data)
                    results[file_id] = boxes
                    print(f"Successfully parsed data for {file_id}")
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON for {file_id}: {e}")
                    # Write the problematic JSON to a file for debugging
                    with open(f"{file_id}_debug.json", 'w', encoding='utf-8') as debug_file:
                        debug_file.write(json_data)
                    print(f"Wrote problematic JSON to {file_id}_debug.json")
    except Exception as e:
        print(f"Error reading CSV file: {e}")
    
    return results

def visualize_contexts(pymupdf_boxes, pdfpig_boxes, pdf_path, output_path):
    """Draw bounding boxes and context overlaps on a PDF"""
    # Open the PDF
    doc = fitz.open(pdf_path)
    
    # Generate random colors
    pymupdf_color = (1, 0, 0)  # Red
    pdfpig_color = (0, 0, 1)   # Blue
    overlap_color = (0, 0.5, 0)  # Green
    
    # Get contexts for each PyMuPDF box
    all_contexts = get_all_contexts(pymupdf_boxes, pdfpig_boxes)
    
    # Find which PDFPig boxes are used as contexts
    used_pdfpig_boxes = set()
    for box_idx, contexts in all_contexts.items():
        for context in contexts:
            for i, box in enumerate(pdfpig_boxes):
                if box.get("text", "") == context:
                    used_pdfpig_boxes.add(i)
    
    # Draw boxes on each page
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_idx = page_num + 1  # 1-based page index
        
        # Draw PyMuPDF boxes (red)
        for i, box in enumerate(pymupdf_boxes):
            if box.get("page", 1) != page_idx:
                continue
                
            x = box.get("x", 0)
            y = box.get("y", 0)
            width = box.get("width", 0)
            height = box.get("height", 0)
            
            rect = fitz.Rect(x, y, x + width, y + height)
            page.draw_rect(rect, color=pymupdf_color, width=0.5)
            
            # Add box index and text snippet
            text = box.get("text", "")
            text_snippet = text[:20] + "..." if len(text) > 20 else text
            # page.insert_text((x, y - 5), f"P{i}: {text_snippet}", fontsize=8, color=(0, 0, 0))
            
            # Draw context indicators
            # contexts = all_contexts.get(i, [])
            # if contexts:
            #     page.insert_text((x, y + height + 10), f"Has {len(contexts)} contexts", fontsize=8, color=overlap_color)
        
        # Draw PDFPig boxes (blue)
        for i, box in enumerate(pdfpig_boxes):
            if box.get("page", 1) != page_idx:
                continue
                
            x = box.get("x", 0)
            y = box.get("y", 0)
            width = box.get("width", 0)
            height = box.get("height", 0)
            
            # Use green for boxes that are used as contexts
            box_color = overlap_color if i in used_pdfpig_boxes else pdfpig_color
            
            rect = fitz.Rect(x, y, x + width, y + height)
            page.draw_rect(rect, color=box_color, width=0.5)
            
            # Add box index and text snippet
            text = box.get("text", "")
            text_snippet = text[:20] + "..." if len(text) > 20 else text
            # page.insert_text((x, y - 5), f"D{i}: {text_snippet}", fontsize=8, color=(0, 0, 0))
    
    # Add a legend
    last_page = doc[-1]
    y_pos = 30
    
    # Add title
    # last_page.insert_text((30, y_pos), "Context Detection Legend", fontsize=12)
    y_pos += 20
    
    # Red boxes: PyMuPDF
    legend_rect = fitz.Rect(30, y_pos, 60, y_pos + 15)
    last_page.draw_rect(legend_rect, color=pymupdf_color, width=0.5)
    last_page.insert_text((70, y_pos + 10), "PyMuPDF Boxes", fontsize=10)
    y_pos += 20
    
    # Blue boxes: PDFPig
    legend_rect = fitz.Rect(30, y_pos, 60, y_pos + 15)
    last_page.draw_rect(legend_rect, color=pdfpig_color, width=0.5)
    last_page.insert_text((70, y_pos + 10), "PDFPig Boxes", fontsize=10)
    y_pos += 20
    
    # Green boxes: Overlapping contexts
    legend_rect = fitz.Rect(30, y_pos, 60, y_pos + 15)
    last_page.draw_rect(legend_rect, color=overlap_color, width=0.5)
    last_page.insert_text((70, y_pos + 10), "Context Overlaps", fontsize=10)
    y_pos += 40
    
    # Add statistics
    # last_page.insert_text((30, y_pos), f"Total PyMuPDF boxes: {len(pymupdf_boxes)}", fontsize=10)
    y_pos += 15
    # last_page.insert_text((30, y_pos), f"Total PDFPig boxes: {len(pdfpig_boxes)}", fontsize=10)
    y_pos += 15
    
    # Count boxes with contexts
    boxes_with_contexts = sum(1 for contexts in all_contexts.values() if contexts)
    # last_page.insert_text((30, y_pos), f"PyMuPDF boxes with contexts: {boxes_with_contexts}", fontsize=10)
    y_pos += 15
    
    # last_page.insert_text((30, y_pos), f"PDFPig boxes used as contexts: {len(used_pdfpig_boxes)}", fontsize=10)
    
    # Save the output PDF
    doc.save(output_path)
    doc.close()
    print(f"Created visualization at {output_path}")

def save_statistics(all_stats, output_dir):
    """Save statistics to both a text file and an Excel file"""
    # Create a DataFrame for Excel output
    df = pd.DataFrame(all_stats)
    
    # Save to Excel
    excel_path = output_dir / "context_detection_stats.xlsx"
    df.to_excel(excel_path, index=False)
    print(f"Saved statistics to Excel: {excel_path}")
    
    # Save to text file
    text_path = output_dir / "context_detection_stats.txt"
    with open(text_path, "w", encoding="utf-8") as f:
        # Write header
        headers = list(all_stats[0].keys())
        f.write("\t".join(headers) + "\n")
        f.write("=" * 80 + "\n")
        
        # Write data
        for stat in all_stats:
            row = [str(stat[header]) for header in headers]
            f.write("\t".join(row) + "\n")
        
        # Write summary
        f.write("\n" + "=" * 80 + "\n")
        f.write("SUMMARY STATISTICS\n")
        f.write("=" * 80 + "\n")
        
        # Calculate averages
        avg_pymupdf = sum(stat["PyMuPDF_Boxes"] for stat in all_stats) / len(all_stats)
        avg_pdfpig = sum(stat["PDFPig_Boxes"] for stat in all_stats) / len(all_stats)
        avg_with_ctx = sum(stat["Boxes_With_Contexts"] for stat in all_stats) / len(all_stats)
        avg_ctx_per_box = sum(stat["Avg_Contexts_Per_Box"] for stat in all_stats) / len(all_stats)
        
        f.write(f"Average PyMuPDF boxes per document: {avg_pymupdf:.2f}\n")
        f.write(f"Average PDFPig boxes per document: {avg_pdfpig:.2f}\n")
        f.write(f"Average boxes with contexts: {avg_with_ctx:.2f}\n")
        f.write(f"Average contexts per box: {avg_ctx_per_box:.2f}\n")
    
    print(f"Saved statistics to text file: {text_path}")

def save_contexts_to_file(pymupdf_boxes, pdfpig_boxes, all_contexts, file_id, output_dir):
    """Save contexts to a text file for manual review"""
    contexts_dir = output_dir / "contexts"
    contexts_dir.mkdir(exist_ok=True)
    
    output_path = contexts_dir / f"{file_id}_contexts.txt"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"CONTEXTS FOR {file_id}\n")
        f.write("=" * 80 + "\n\n")
        
        for box_idx, contexts in all_contexts.items():
            if box_idx < len(pymupdf_boxes):
                box = pymupdf_boxes[box_idx]
                
                # Write box information
                f.write(f"BOX {box_idx} (Page {box.get('page', 1)}):\n")
                f.write("-" * 80 + "\n")
                
                # Write box text
                box_text = box.get("text", "").strip()
                f.write(f"TEXT: {box_text}\n\n")
                
                # Write contexts
                f.write(f"CONTEXTS ({len(contexts)}):\n")
                if contexts:
                    for i, context in enumerate(contexts):
                        f.write(f"  {i+1}. {context}\n")
                        f.write("-" * 40 + "\n")
                else:
                    f.write("  No contexts found\n")
                
                f.write("\n" + "=" * 80 + "\n\n")
    
    print(f"Saved contexts to: {output_path}")

def print_sample_contexts(all_contexts, pymupdf_boxes, max_samples=3):
    """Print a sample of contexts for quick review"""
    print("\nSAMPLE CONTEXTS:")
    print("=" * 80)
    
    # Find boxes with contexts
    boxes_with_context = [box_idx for box_idx, contexts in all_contexts.items() if contexts]
    
    if not boxes_with_context:
        print("No contexts found in any box!")
        return
    
    # Pick a few random boxes to display
    sample_boxes = random.sample(boxes_with_context, min(max_samples, len(boxes_with_context)))
    
    for box_idx in sample_boxes:
        if box_idx < len(pymupdf_boxes):
            box = pymupdf_boxes[box_idx]
            contexts = all_contexts[box_idx]
            
            print(f"\nBOX {box_idx} (Page {box.get('page', 1)}):")
            print(f"TEXT: {box.get('text', '')[:100]}...")
            print(f"CONTEXTS ({len(contexts)}):")
            
            # Print first context (or part of it)
            if contexts:
                first_context = contexts[0]
                print(f"  1. {first_context[:100]}...")
                if len(contexts) > 1:
                    print(f"  ... and {len(contexts)-1} more contexts")
            
            print("-" * 80)
    
    print("\nFull contexts available in text files.")

def main():
    # File paths
    pymupdf_csv = "submission_ocr_official.csv"  
    pdfpig_csv = "submission_pdfpig.csv"
    
    # PDF directories to search
    pdf_dirs = [
        Path("data/test/PDF"),
        Path("data/test/PDF_scaled"),
        Path("data/test/PDF_ocr")
    ]
    
    output_dir = Path("context_detection_results")
    output_dir.mkdir(exist_ok=True)
    
    # Load CSV data
    pymupdf_data = load_csv_data_pymupdf(pymupdf_csv)
    pdfpig_data = load_csv_data_pdfpig(pdfpig_csv)
    
    # Process each file that exists in both datasets
    common_files = set(pymupdf_data.keys()).intersection(set(pdfpig_data.keys()))
    print(f"Found {len(common_files)} common files between PyMuPDF and PDFPig outputs")
    
    # Storage for all statistics
    all_stats = []
    
    # Also store detailed context data for advanced analysis
    context_details = []
    
    for file_id in common_files:
        # Try to find PDF file in various directories
        pdf_path = find_pdf_file(file_id, pdf_dirs)
        
        if pdf_path:
            print(f"Processing {file_id}...")
            pymupdf_boxes = pymupdf_data[file_id]
            pdfpig_boxes = pdfpig_data[file_id]
            
            # Calculate overlap statistics
            all_contexts = get_all_contexts(pymupdf_boxes, pdfpig_boxes)
            
            # Save contexts to a text file for manual review
            save_contexts_to_file(pymupdf_boxes, pdfpig_boxes, all_contexts, file_id, output_dir)
            
            # Still create the visualization PDF if wanted
            output_path = output_dir / "pdfs" / f"{file_id}_contexts.pdf"
            os.makedirs(output_dir / "pdfs", exist_ok=True)
            visualize_contexts(pymupdf_boxes, pdfpig_boxes, str(pdf_path), str(output_path))
            
            boxes_with_contexts = sum(1 for contexts in all_contexts.values() if contexts)
            
            # Calculate average contexts per box
            total_contexts = sum(len(c) for c in all_contexts.values())
            avg_contexts = total_contexts / len(pymupdf_boxes) if pymupdf_boxes else 0
            
            # Store statistics for this file
            stats = {
                "File_ID": file_id,
                "PyMuPDF_Boxes": len(pymupdf_boxes),
                "PDFPig_Boxes": len(pdfpig_boxes),
                "Boxes_With_Contexts": boxes_with_contexts,
                "Avg_Contexts_Per_Box": round(avg_contexts, 2),
                "Context_Coverage": round(boxes_with_contexts / len(pymupdf_boxes) * 100, 2) if pymupdf_boxes else 0
            }
            all_stats.append(stats)
            
            # Store detailed context data
            for box_idx, contexts in all_contexts.items():
                if box_idx < len(pymupdf_boxes):
                    box = pymupdf_boxes[box_idx]
                    detail = {
                        "File_ID": file_id,
                        "Box_Index": box_idx,
                        "Text": box.get("text", "")[:50],  # Truncate long text
                        "Num_Contexts": len(contexts),
                        "Has_Context": len(contexts) > 0,
                        "Page": box.get("page", 1),
                        "X": box.get("x", 0),
                        "Y": box.get("y", 0),
                        "Width": box.get("width", 0),
                        "Height": box.get("height", 0)
                    }
                    context_details.append(detail)
            
            print(f"  - PyMuPDF boxes: {len(pymupdf_boxes)}")
            print(f"  - PDFPig boxes: {len(pdfpig_boxes)}")
            print(f"  - PyMuPDF boxes with contexts: {boxes_with_contexts}")
            print(f"  - Average contexts per box: {avg_contexts:.2f}")
            
            # If this is the first file, print some sample contexts
            if not all_stats or len(all_stats) == 1:
                print_sample_contexts(all_contexts, pymupdf_boxes)
        else:
            print(f"PDF file not found for {file_id}. Skipping...")
    
    # Save all statistics
    if all_stats:
        save_statistics(all_stats, output_dir)
        
        # Save detailed context data to Excel for deeper analysis
        details_df = pd.DataFrame(context_details)
        details_path = output_dir / "context_details.xlsx"
        details_df.to_excel(details_path, index=False)
        print(f"Saved detailed context information to: {details_path}")
    else:
        print("No files were processed successfully. Check your file paths and data.")

def find_pdf_file(file_id: str, search_dirs: List[Path]) -> Optional[Path]:
    """
    Search for a PDF file with the given ID in multiple directories
    
    Args:
        file_id: The ID of the file to search for
        search_dirs: List of directories to search in
        
    Returns:
        Path to the PDF file if found, None otherwise
    """
    # All possible filename variations to try
    name_variations = [
        f"{file_id}.pdf",
        f"{file_id}.coco_standard.pdf",
        f"{file_id}.ocr.pdf"
    ]
    
    # Search in all directories
    for dir_path in search_dirs:
        for name in name_variations:
            pdf_path = dir_path / name
            if (pdf_path.exists()):
                return pdf_path
    
    return None

if __name__ == "__main__":
    main()