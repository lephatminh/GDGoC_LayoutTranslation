import csv
import json


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