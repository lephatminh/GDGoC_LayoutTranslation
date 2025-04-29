import csv

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