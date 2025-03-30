import csv
import os
import re

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

def fix_submission_format(input_file, output_file=None):
    """Fix the format of the solution column by removing ONLY the outer quotes around JSON arrays"""
    
    if output_file is None:
        # If no output file specified, create a temporary file and then replace the input
        output_file = input_file + ".fixed"
        replace_original = True
    else:
        replace_original = False
    
    # Read the input file
    rows = []
    with open(input_file, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)  # Get header
        rows.append(header)
        
        for row in reader:
            if len(row) >= 2:
                # Get the raw solution content from the original file
                with open(input_file, 'r', encoding='utf-8') as raw_file:
                    raw_content = raw_file.read()
                    # Find the row by ID
                    pattern = f"{row[0]},\"(\\[.*?\\])\"$"
                    match = re.search(pattern, raw_content, re.MULTILINE | re.DOTALL)
                    if match:
                        # Keep the ID from the row, but use the raw solution without outer quotes
                        rows.append([row[0], match.group(1)])
                    else:
                        # If no match found, use the row as is
                        rows.append(row)
    
    # Write to output file with QUOTE_NONE to avoid quoting the JSON arrays
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        # Create a custom dialect that doesn't quote fields
        class CustomDialect(csv.excel):
            quoting = csv.QUOTE_NONE
            escapechar = '\\'  # Use backslash to escape special characters if needed
        
        # Register our custom dialect
        csv.register_dialect('custom', CustomDialect)
        
        # Use the custom dialect
        writer = csv.writer(f, dialect='custom')
        writer.writerows(rows)
    
    if replace_original:
        # Replace the original file with the fixed version
        os.replace(output_file, input_file)
        print(f"Fixed format in {input_file}")
    else:
        print(f"Fixed format written to {output_file}")

# Run the function
fix_submission_format("submission.csv")