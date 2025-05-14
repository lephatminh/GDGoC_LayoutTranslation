import fitz
import os
import json


def convert_point_to_box(coor):
    '''
    Convert two points (x1, y1) as top-left and (x2, y2) as bottom-right to a box (x, y, width, height).
    
    Args:
    coor = [x1,y1,x2,y2]
        x1 (float): x-coordinate of the top-left point
        y1 (float): y-coordinate of the top-left point
        x2 (float): x-coordinate of the bottom-right point
        y2 (float): y-coordinate of the bottom-right point
    
    Returns:
        list: A list [x, y, width, height] representing the box
    
    Raises:
        ValueError: If x2 < x1 or y2 < y1, indicating an invalid rectangle
    '''
    x1,y1,x2,y2 = coor

    # Validate that bottom-right is to the right and below top-left
    if x2 < x1 or y2 < y1:
        raise ValueError("Invalid rectangle: x2 must be >= x1 and y2 must be >= y1")
    
    # Top-left corner is (x1, y1)
    x = x1
    y = y1
    
    # Width = x2 - x1, Height = y2 - y1
    width = x2 - x1
    height = y2 - y1
    
    return [x, y, width, height]


def check_overlap(cell, math_box):
    '''
    Checking the overlap of the math box and cell in cell list

    Args: 
    cell: {'x', 'y', 'width', 'height',...}
    math_box: [x_box, y_box, width_box, height_box]

    Returns:
    True/False
    '''
    x1, y1, width_1, height_1 = [cell['x'], cell['y'], cell['width'], cell['height']]
    x2, y2, width_2, height_2 = math_box
    
    # Check if one box is to the left of the other
    if x1 + width_1 < x2 or x2 + width_2 < x1:
        return False
    elif x2 + width_2 < x1 or x1 + width_1 < x2:
        return False

    # Check if one box is above the other
    if y1 + height_1 < y2 or y2 + height_2 < y1:
        return False
    elif y2 + height_2 < y1 or y1 + height_1 < y2:
        return False
    
    # If neither condition is true, the boxes overlap
    return True


def overlap_ratio(cell, math_box):
    '''
    Calculate the overlap ratio and return it with the coordinates of the overlapping rectangle.
    
    Args:
        cell: {'x', 'y', 'width', 'height',...} - coordinates and dimensions of the cell
        math_box (list): [x_box, y_box, width_box, height_box] - coordinates and dimensions of the math box
    
    Returns:
        list: [ratio, x, y, width, height] where:
              - ratio (float): Percentage of the cell's area that overlaps with the math box
              - x, y (float): Top-left corner of the overlapping rectangle
              - width, height (float): Dimensions of the overlapping rectangle
              Returns [0.0, 0, 0, 0, 0] if no overlap or if cell has zero area
    '''
    # Extract coordinates and dimensions
    x1, y1, width_cell, height_cell = [cell['x'], cell['y'], cell['width'], cell['height']]
    x2, y2, width_box, height_box = math_box
    
    # Calculate the coordinates of the overlapping rectangle
    x_left = max(x1, x2)
    x_right = min(x1 + width_cell, x2 + width_box)
    y_top = max(y1, y2)
    y_bottom = min(y1 + height_cell, y2 + height_box)
    
    # Check if there is an overlap
    if x_right <= x_left or y_bottom <= y_top:
        return [0.0, 0, 0, 0, 0]  # No overlap
    
    # Calculate the area of the overlapping rectangle
    overlap_width = x_right - x_left
    overlap_height = y_bottom - y_top
    overlap_area = overlap_width * overlap_height
    
    # Calculate the area of the cell
    cell_area = width_cell * height_cell
    
    # Avoid division by zero (if cell has zero area)
    if cell_area == 0:
        return [0.0, 0, 0, 0, 0]
    
    # Calculate the overlap ratio as a percentage
    ratio = (overlap_area / cell_area) * 100
    
    # Return the ratio and overlap coordinates
    return [ratio, x_left, y_top, overlap_width, overlap_height]


def get_box_overlap(cells, math_box):
    '''
    Get all overlap (interact cell) from list of cells and a given math box

    Args:
        cells: list of Cells [{'x','y','width','height',...},...]
        box: [x,y,width,height]

    Output:
        not_overlap_list: []
    '''
    overlap_list = []

    not_overlap_list = []

    # Very important: need to extract

    for cell in cells:
        if (check_overlap(cell, math_box)):
            overlap_info = overlap_ratio(cell, math_box)
            overlap_rate = overlap_info[0]
            overlap_box = overlap_info[1:]

            #print('Overlap ratio:', overlap_rate, 'Overlap box:', overlap_box)

            if overlap_rate > 40.0:
                overlap_list.append(cell)
            else:
                not_overlap_list.append([cell, overlap_box])

    return not_overlap_list, overlap_list


def box_increasement(cell, math_box):
    '''
    Perform the box increasement

    Args:
        cell: {'x', 'y', 'width', 'height',...} - coordinates and dimensions of the cell
        math_box : [x_box, y_box, width_box, height_box] - coordinates and dimensions of the math box
    
    Return:
        box_increasement: [min(x_cell, x_box), min(y_cell, y_box), new_widht, new_height]
    '''
    x1, y1, w1, h1 = [cell["x"], cell["y"], cell["width"], cell["height"]]
    x2, y2, w2, h2 = math_box

    x_new = min(x1,x2)
    y_new = min(y1, y2)

    diff_x = x2 - x1
    diff_y = y2 - y1

    w_new = w2
    h_new = h2

    if diff_x > 0: # ( x_new = x1) 
        if w1 - abs(diff_x) >  w2:
            w_new = w1
        else:
            w_new = w2 + abs(diff_x)		
    else: # (x_new = x2)
        if w2 - abs(diff_x) > w1:
            w_new = w2
        else:
            w_new = w1 + abs(diff_x)	

    if diff_y > 0: # ( y_new = y1) 
        if h1 - abs(diff_y) >  h2:
            h_new = h1
        else:
            h_new = h2 + abs(diff_y)		
    else: #(y_new = y2)
        if h2 - abs(diff_y) > h1:
            h_new = h2
        else:
            h_new = h1 + abs(diff_y)	


    increasement_box = [x_new, y_new, w_new, h_new]

    return increasement_box


def box_increasement_from_list(overlap_list, math_box):
    '''
    Perform the increasement for a given box with respect to give overlap list

    Args:
    overlap_list: 
        [{'x', 'y', 'width', 'height',...},...]
    math_box:
        [x,y,w,h]
    '''

    math_box = math_box

    for cell in overlap_list:
        math_box = box_increasement(cell, math_box)

    return math_box


def box_overlap_list(cells, math_box):
    '''
    Get the: 
        overlap -> [[{'x', 'y', 'height', 'width','text'},['x','y','width','height']],...]  
    and 
        non overlap cell -> [{'x', 'y', 'height', 'width',...},...]

    Perform the box increasement

    Args:
    cells: list of Cell, each cell is a list [x,y,width,height] 
    box: [x,y,width,height]

    Returns:
        overlap cell list
    '''

    overlap_list = []

    not_overlap_list = []

    math_box = math_box

    not_overlap_list, overlap_list = get_box_overlap(cells, math_box)

    math_box = box_increasement_from_list(overlap_list, math_box)

    return math_box, not_overlap_list, overlap_list


def cut_cells_box(pdf ,cut_cells, no_cutted_cell_id):
    '''
    Perform the overlap cutting from the given cell

    Args:
        pdf: PDF path with respect to the cell
        cut_cells: List of cells and its cutted box 
            [[{'x', 'y', 'width', 'height', ...},[x, y, width, height]],...]
        no_cutted_cell_id: This is list of id of cell that not performed the cut

    Return:
        List of  Re-text and rebox the cell
            [{'x', 'y', 'width', 'height', 'text'},...]
    '''

    # Open the PDF
    doc = fitz.open(pdf)

    # Choose the page
    page = doc[0]  # first page (0-based index)

    def get_new_cell(page, cut_cell):
    # Step 1: Get the text from one region
        x1, y1, w, h = cut_cell[1]
        x2 = x1 + w
        y2 = y1 + h

        # Define the snipping rectangle (x0, y0, x1, y1)
        # Units are in points (1/72 inch)
        rect = fitz.Rect(x1, y1, x2, y2)

        # Extract text from the defined region
        text = page.get_textbox(rect)

        #print(text)

        # Step 2: Reconstruct the cell

        new_cell = cut_cell[0].copy()

        #print(new_cell["text"])

        new_cell['text'] =  new_cell['text'].replace(text.strip(), '')    
        new_cell['x'] = new_cell['x'] + w
        new_cell['width'] = new_cell['width'] - w

        return new_cell
    
    cutted_cell_list = []

    for cell in cut_cells:
        if (cell[0]['id'] not in no_cutted_cell_id):
            cell_place_holder = get_new_cell(page, cell)
            cutted_cell_list.append(cell_place_holder)
        else:
            continue

    return cutted_cell_list


def load_math_boxes(root_folder):
    '''
    Load the .txt file which is called 'pdf_coor.txt' in the given folder.

    The 'pdf_coor.txt' in the folder contains many rows, each with the format:
        1 12.5 13.4 50.3 60.6
    These are 5 values respectively:
        - id
        - x_left
        - y_left
        - x_right
        - y_right

    Converts each row to (id, x_left, y_left, width, height)

    Args:
    root_folder: str - Path to the folder (e.g., './Math_notation')

    Returns:
    List of dicts with format: 
    {'id': id, 'x': x_left, 'y': y_left, 'width': width, 'height': height}
    '''
    file_path = os.path.join(root_folder, 'pdf_coor.txt')
    boxes = []

    with open(file_path, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) != 5:
                continue  # Skip malformed lines
            try:
                id_, x_left, y_left, x_right, y_right = map(float, parts)
                box = {
                    'id': int(id_),
                    'x': x_left,
                    'y': y_left,
                    'width': x_right - x_left,
                    'height': y_right - y_left
                }
                boxes.append(box)
            except ValueError:
                continue  # Skip lines with invalid values

    return boxes


def insert_cell_id(cells):
    '''
    Insert unique Id for each cell

    And

    Cell original overlap list (as many box may resi)

    Args:
        cells: List of cells
            [{'x','y', 'width', 'height', 'text',..},...]

    Output:
        new_cells: List of cells with id:
            [{'id', 'x', 'y', 'width', 'height', 'text',...},...]
    '''

    cells = cells
    
    cnt = 1

    for cell in cells:
        cell['id'] = cnt
        cnt = cnt + 1

    return cells


def reconstruct_text_cell(cells, math_box_list):
    '''
    For each math_box in the math_box_list:
        1. Find all the Overlap (actually interact) cell in cells
        2.
            - Merge the math_box with overlaped cell with ratio > 40%
            - Perform the cell cutting with overlaped cell with ratio <= 40%
        3. Return the boxes, merge boxs, cells and reconstruct cells

    Args:
        pdf: pdf with respect to the cell and math_box
        cells: list of cells
            [{'x', 'y', 'width', 'height', 'text', ...},]
        math_box_list: list of box
            [{'id', 'x', 'y', 'width', 'height'}]

    Return:
        List of box: 
            [{'id', 'x', 'y', 'width', 'height'},...]
        New cells list: 
            [{'x', 'y', 'width', 'height', 'text',...},...]
    '''
    cells = cells

    merged_boxes = []

    overlap_id_list = []

    cut_cell_list = [] # not overlaped and will perform the cut

    cut_cell_list_id = []

    for box in math_box_list:
        original_box = box
        
        original_box_coor = [original_box['x'], 
                             original_box['y'], 
                             original_box['width'],
                             original_box['height']]

        #print(original_box)
        
        merge_box, cut_cell_list_box, overlap_list_box = box_overlap_list(cells, original_box_coor)  

        #print('Overlap_list:', overlap_list_box, '\n')

        if (len(overlap_list_box) > 0):
            overlap_id_list.extend([tmp['id'] for tmp in overlap_list_box ])

        if (len(cut_cell_list_box) > 0):
            #print(cut_cell_list_box)
            cut_cell_list.extend(cut_cell_list_box)

            cut_cell_list_id.extend(tmp[0]['id'] for tmp in cut_cell_list_box)

        box_holder = {
            'id' : original_box['id'],
            'x' : merge_box[0],
            'y' : merge_box[1],
            'width' : merge_box[2],
            'height' : merge_box[3]
        }

        merged_boxes.append(box_holder)

        # print('Merge_box:', merge_box)
        # print('Cut_cell_list:', cut_cell_list_box)
        #print('Overlap_list:', overlap_list_box)

        # print('-----------------------')
    
    remain_cell_list_id = [tmp['id'] for tmp in cells if tmp['id'] not in overlap_id_list and tmp['id'] not in cut_cell_list_id]

    #print('Overlap_list (will be not used):', overlap_id_list)
    #print('Reconstruct the text cell (re OCR and cut cell):' ,cut_cell_list_id)
    #print('The remaing cells kept normal:',remain_cell_list_id)


    return merged_boxes, overlap_id_list, cut_cell_list, remain_cell_list_id


def reconstruct_text_cell_from_file(pdf_name, output_path):

    def load_layout_cells(file_name):
        # Open the JSON file and load the data
        with open(file_name, 'r') as json_file:
            data = json.load(json_file)
        return data

    math_box_list = load_math_boxes(pdf_name)

    cells = load_layout_cells(pdf_name + '/' + pdf_name + '.json')

    cells = insert_cell_id(cells)

    merged_boxes, overlap_id_list, cut_cell_list, remain_cell_list_id = reconstruct_text_cell(cells, math_box_list)

    cutted_cells = cut_cells_box(pdf_name + '.pdf', cut_cell_list, remain_cell_list_id)

    remain_cell = [cell for cell in cells if cell['id'] in remain_cell_list_id]

    all_cells = cutted_cells + remain_cell

    def export_math_boxes_and_text_cells(cells_text, math_box, folder_name):
        """
        Creates a new folder and writes two files:
        - 'reconstruct_translated_pdf.json' with the full list of dicts
        - 'pdf_coor.txt' with space-separated values: id x y width height

        Args:
            cells_text (list of dict): List of box dictionaries
            math_box (list of dict): List of dictionaries
            folder_name (str): Name of the new folder to create
        """
        # folder_name = folder_name + '_processed'

        os.makedirs(folder_name, exist_ok=True)  # Create folder if it doesn't exist

        # Write JSON file
        json_path = os.path.join(folder_name, pdf_name + '.json')
        with open(json_path, 'w') as json_file:
            json.dump(cells_text, json_file, indent=4)

        # Write txt file
        txt_path = os.path.join(folder_name, 'pdf_coor.txt')
        with open(txt_path, 'w') as txt_file:
            for item in math_box:
                line = f"{item['id']} {item['x']} {item['y']} {item['width']} {item['height']}"
                txt_file.write(line + '\n')

        print(f"Files saved in: {folder_name}")
    
    export_math_boxes_and_text_cells(all_cells, merged_boxes, output_path)