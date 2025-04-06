import csv
import os
import json
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

def transform_bboxes_in_json(json_obj):
    """Recursively transform all bbox arrays to x,y,width,height format in a JSON object"""
    if isinstance(json_obj, dict):
        # Process this dictionary
        if 'bbox' in json_obj and isinstance(json_obj['bbox'], list) and len(json_obj['bbox']) >= 4:
            # Extract bbox values
            bbox = json_obj['bbox']
            # Add individual coordinates
            json_obj['x'] = bbox[0]
            json_obj['y'] = bbox[1]
            json_obj['width'] = bbox[2]
            json_obj['height'] = bbox[3]
            # Remove the original bbox
            del json_obj['bbox']
        
        # Process all values in this dictionary
        for key, value in json_obj.items():
            json_obj[key] = transform_bboxes_in_json(value)
            
    elif isinstance(json_obj, list):
        # Process all items in this list
        for i, item in enumerate(json_obj):
            json_obj[i] = transform_bboxes_in_json(item)
    
    return json_obj

def convert_bbox_format(input_file, output_file):
    # First verify the input file structure
    with open(input_file, 'r', newline='', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames)
        print(f"Input file columns: {fieldnames}")
        
        # Ensure we're working with just id and solution
        if len(fieldnames) != 2 or 'id' not in fieldnames or 'solution' not in fieldnames:
            print(f"WARNING: Unexpected column structure. Expected 'id' and 'solution', got {fieldnames}")
    
    # Process the rows
    with open(input_file, 'r', newline='', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        
        # Ensure output has same structure as input (just id and solution)
        with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            
            rows_processed = 0
            bboxes_transformed = 0
            
            for row in reader:
                rows_processed += 1
                if 'solution' in row and row['solution']:
                    try:
                        # Parse the JSON solution
                        solution_data = json.loads(row['solution'])
                        
                        # Transform all bboxes in the solution JSON
                        transformed_solution = transform_bboxes_in_json(solution_data)
                        
                        # Convert back to JSON string
                        row['solution'] = json.dumps(transformed_solution, ensure_ascii=False)
                        bboxes_transformed += 1
                        
                    except Exception as e:
                        # Print the error but continue processing
                        print(f"Error processing row {rows_processed} (id: {row.get('id', 'unknown')}): {str(e)[:100]}...")
                
                writer.writerow(row)
            
            print(f"Processed {rows_processed} rows, transformed bboxes in {bboxes_transformed} rows")
    
    # Verify the output structure
    with open(output_file, 'r', newline='', encoding='utf-8') as outfile:
        reader = csv.DictReader(outfile)
        output_fieldnames = list(reader.fieldnames)
        print(f"Output file columns: {output_fieldnames}")
        
        if output_fieldnames != fieldnames:
            print(f"WARNING: Output column structure does not match input. Expected {fieldnames}, got {output_fieldnames}")

    print(f"Conversion complete. Output saved to {output_file}")

if __name__ == "__main__":
    input_file = "submission_fill.csv"
    output_file = "submission_official.csv"
    
    if os.path.exists(input_file):
        convert_bbox_format(input_file, output_file)
    else:
        print(f"Error: Input file '{input_file}' not found.")