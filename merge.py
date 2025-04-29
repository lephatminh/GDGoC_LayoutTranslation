import csv
import os
from core.csv_utils import find_max_csv_field_size


csv.field_size_limit(find_max_csv_field_size())


def merge_submission_files(part_files, output_file, sample_file):
    """
    Merge multiple submission CSV files into a single file.
    Only includes IDs that are present in the sample submission file.
    
    Args:
        part_files: List of input CSV files to merge
        output_file: Path for the merged output file
        sample_file: Path to sample submission file with valid IDs
    """
    # Load valid IDs from sample submission
    valid_ids = set()
    with open(sample_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            if row and len(row) > 0:
                valid_ids.add(row[0])
    
    print(f"Loaded {len(valid_ids)} valid IDs from sample submission")
    
    # Open output file for writing
    with open(output_file, 'w', newline='', encoding='utf-8') as out_file:
        writer = csv.writer(out_file)
        writer.writerow(["id", "solution"])  # Write header
        
        # Track stats
        total_processed = 0
        total_included = 0
        total_skipped_invalid = 0
        total_skipped_empty = 0
        
        # Process each part file
        for part_file in part_files:
            if not os.path.exists(part_file):
                print(f"Warning: File {part_file} not found, skipping.")
                continue
                
            print(f"Processing {part_file}...")
            part_included = 0
            part_skipped_invalid = 0
            part_skipped_empty = 0
            
            # Open and read the part file
            with open(part_file, 'r', newline='', encoding='utf-8') as in_file:
                reader = csv.reader(in_file)
                
                # Skip header row
                try:
                    next(reader)
                    
                    # Process all data rows
                    for row in reader:
                        total_processed += 1
                        
                        if len(row) < 2:  # Skip malformed rows
                            continue
                            
                        file_id, solution = row[0], row[1]
                        
                        # Check if ID exists in sample submission
                        if file_id not in valid_ids:
                            part_skipped_invalid += 1
                            continue
                            
                        # Skip empty solutions
                        # if solution.strip() in ['[]', '""[]""', '{}', '""{}""']:
                        #     part_skipped_empty += 1
                        #     continue
                            
                        # Write the validated row
                        writer.writerow([file_id, solution])
                        part_included += 1
                            
                except StopIteration:
                    print(f"  File {part_file} appears to be empty or has only header.")
            
            print(f"  Added {part_included} rows from {part_file}")
            print(f"  Skipped {part_skipped_invalid} invalid IDs not in sample submission")
            print(f"  Skipped {part_skipped_empty} rows with empty solutions")
            
            total_included += part_included
            total_skipped_invalid += part_skipped_invalid
            total_skipped_empty += part_skipped_empty
    
    print(f"\nMerge complete!")
    print(f"Total rows processed: {total_processed}")
    print(f"Total rows included: {total_included}")
    print(f"Total invalid IDs skipped: {total_skipped_invalid}")
    print(f"Total empty solutions skipped: {total_skipped_empty}")
    print(f"Output file: {output_file}")
    print(f"File size: {os.path.getsize(output_file) / (1024*1024):.2f} MB")

if __name__ == "__main__":
    # List all submission part files in order
    part_files = [
        "submission_ocr_official_part_1.csv", 
        "submission_ocr_official_part_2.csv", 
        "submission_ocr_official_part_3.csv", 
        "submission_ocr_official_part_4.csv"
    ]
    
    # Sample submission file with valid IDs
    sample_file = "sample_submission.csv"
    
    # Output file
    output_file = "submission.csv"
    
    # Run the merge
    merge_submission_files(part_files, output_file, sample_file)
    
    print("\nVerifying the first few rows of output file:")
    # Print first 2 rows to verify format
    with open(output_file, 'r', encoding='utf-8') as f:
        lines = [f.readline().strip() for _ in range(3)]
        for line in lines:
            if len(line) > 100:
                # Truncate long lines for display
                print(f"{line[:50]}...{line[-50:]}")
            else:
                print(line)