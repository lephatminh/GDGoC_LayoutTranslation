import os, glob, gc, shutil, yaml
from IPython.display import clear_output
from tqdm.notebook import tqdm
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import cv2
import torch
from ultralytics import YOLO
from pdf2image import convert_from_path
import fitz  # PyMuPDF
import os
from pathlib import Path
from typing import List, Tuple

IMAGE_SIZE = (2048, 1447)
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.75
FONT_THICKNESS = 2
BORDER_THICKNESS = 2

RANDOM_STATE = 42
INPUT_SIZE = 1024
N_EPOCHS = 15
PATIENCE = 5
BATCH_SIZE = 4
CACHE_DATA = True
DEVICES = 1

def pdf_to_jpg_with_sizes(pdf_path, output_folder, dpi=300):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    pdf_name = os.path.basename(pdf_path).replace('.pdf','')

    # Convert PDF to images
    images = convert_from_path(pdf_path, dpi=dpi)

    # Get PDF page sizes using PyMuPDF
    pdf_doc = fitz.open(pdf_path)

    # Use first page for size.txt (assuming all pages same size)
    first_image = images[0]
    first_page = pdf_doc[0]

    # Get sizes
    jpg_size = first_image.size  # (width, height) in pixels
    pdf_size = (first_page.rect.width, first_page.rect.height)  # (width, height) in points

    # Write to size.txt
    size_txt_path = os.path.join(output_folder, 'size.txt')
    with open(size_txt_path, 'w') as f:
        f.write(f"{jpg_size}\n")
        f.write(f"{pdf_size}\n")
    print(f"Saved size.txt at {size_txt_path}")

    # Save JPGs and print sizes
    for i, (image, page) in enumerate(zip(images, pdf_doc)):
        jpg_path = os.path.join(output_folder, f'{pdf_name}.jpg')
        image.save(jpg_path, 'JPEG')

        print(f'Page {i+1}: PDF size = {pdf_size[0]} x {pdf_size[1]} pt, JPG size = {jpg_size[0]} x {jpg_size[1]} px')
        print(f'Saved: {jpg_path}')

def scale_box_to_pdf(jpg_box, jpg_size, pdf_size):
    x1, y1, x2, y2 = jpg_box
    jpg_width, jpg_height = jpg_size
    pdf_width, pdf_height = pdf_size

    scale_x = pdf_width / jpg_width
    scale_y = pdf_height / jpg_height

    scaled_x1 = x1 * scale_x
    scaled_y1 = y1 * scale_y
    scaled_x2 = x2 * scale_x
    scaled_y2 = y2 * scale_y

    return [scaled_x1, scaled_y1, scaled_x2, scaled_y2]

def generate_pdf_coordinates(image_folder):
    """
    Generate pdf_coor.txt with PDF-scaled coordinates from index.txt and size.txt.

    Args:
        image_folder (str): Folder containing index.txt, size.txt, and images.
    """
    import ast

    # Load size.txt
    size_path = os.path.join(image_folder, 'size.txt')
    with open(size_path, 'r') as f:
        jpg_size = ast.literal_eval(f.readline().strip())
        pdf_size = ast.literal_eval(f.readline().strip())

    # Load index.txt
    index_path = os.path.join(image_folder, 'index.txt')
    with open(index_path, 'r') as f:
        lines = f.readlines()

    pdf_coordinates = []

    for line in lines:
        parts = line.strip().split()
        if len(parts) != 5:
            continue  # skip bad lines

        box_id, x1, y1, x2, y2 = parts
        x1, y1, x2, y2 = map(float, [x1, y1, x2, y2])

        # Convert coordinates to PDF space
        scaled_box = scale_box_to_pdf([x1, y1, x2, y2], jpg_size, pdf_size)

        # Format line for output
        pdf_line = f"{box_id} {scaled_box[0]:.4f} {scaled_box[1]:.4f} {scaled_box[2]:.4f} {scaled_box[3]:.4f}"
        pdf_coordinates.append(pdf_line)

    # Save to pdf_coor.txt
    pdf_coor_path = os.path.join(image_folder, 'pdf_coor.txt')
    with open(pdf_coor_path, 'w') as f:
        for line in pdf_coordinates:
            f.write(line + '\n')

    print(f"PDF coordinates saved at: {pdf_coor_path}")

def crop_and_normalize_all(output_path):
    """
    Process all .jpg and .txt pairs in root folder, crop boxes, rename txt files,
    and save normalized data with float coordinates.

    Args:
        output_path (str): Root folder containing .jpg and .txt files.
    """
    # Create images folder
    images_folder = os.path.join(output_path, 'images')
    os.makedirs(images_folder, exist_ok=True)

    # Find all jpg files
    jpg_files = glob.glob(os.path.join(output_path, '*.jpg'))

    for jpg_path in jpg_files:
        base_name = os.path.splitext(os.path.basename(jpg_path))[0]
        txt_path = os.path.join(output_path, f'{base_name}.txt')

        if not os.path.exists(txt_path):
            print(f'Skipping {base_name}: no matching txt file.')
            continue

        # Load image
        image = cv2.imread(jpg_path)
        h_img, w_img = image.shape[:2]

        # Read txt file
        with open(txt_path, 'r') as f:
            lines = f.readlines()

        normalized_lines = []

        for i, line in enumerate(lines):
            parts = line.strip().split()
            if len(parts) != 5:
                continue  # skip bad lines

            box_id = i + 1
            x1, y1, x2, y2 = map(float, parts[1:])

            # Apply ±5 adjustment
            y1_adj = y1 - 5
            y2_adj = y2 + 5

            # Clamp coordinates within image boundaries
            x1_clamped = max(0.0, x1)
            y1_clamped = max(0.0, y1_adj)
            x2_clamped = min(float(w_img), x2)
            y2_clamped = min(float(h_img), y2_adj)

            # Crop image using int for pixel slicing
            crop = image[int(y1_clamped):int(y2_clamped), int(x1_clamped):int(x2_clamped)]

            # Save as images/id.jpg (only id, no prefix)
            crop_filename = f'{box_id}.jpg'
            crop_path = os.path.join(images_folder, crop_filename)
            cv2.imwrite(crop_path, crop)
            print(f'Saved: {crop_path}')

            # Save normalized line with float precision (4 decimal places)
            normalized_line = f"{box_id} {x1_clamped:.4f} {y1_clamped:.4f} {x2_clamped:.4f} {y2_clamped:.4f}"
            normalized_lines.append(normalized_line)

        # # Rename original txt → conf.txt (no prefix)
        # conf_txt_path = os.path.join(root_folder, 'conf.txt')
        # os.rename(txt_path, conf_txt_path)
        # print(f'Renamed {txt_path} → {conf_txt_path}')

        # Save normalized txt as index.txt (no prefix)
        index_txt_path = os.path.join(output_path, 'index.txt')
        with open(index_txt_path, 'w') as f:
            for line in normalized_lines:
                f.write(line + '\n')

        generate_pdf_coordinates(output_path)

        print(f'Index txt saved at: {index_txt_path}')

def detect_math_box_images(name_root, output_path, best_model):
    pdf_to_jpg_with_sizes(name_root, output_path)
    
    with torch.no_grad():
        predictions = best_model.predict(
                source= output_path,
                conf=0.65,
                iou=0.75,
                stream=True
            )

    test_images = []

    for prediction in predictions:
        if len(prediction.boxes.xyxy):
            name = prediction.path.split("/")[-1].split(".")[0]
            boxes = prediction.boxes.xyxy.cpu().numpy()
            scores = prediction.boxes.conf.cpu().numpy()
            
            test_images += [name]
            label_path = os.path.join(output_path, name + ".txt")
            
            with open(label_path, "w+") as f:
                for score, box in zip(scores, boxes):
                    text = f"{score:0.4f} {' '.join(box.astype(str))}"
                    f.write(text)
                    f.write("\n")

    clear_output()

    crop_and_normalize_all(output_path)

# best_weights = "best.pt"
# best_model = YOLO(best_weights)

# name_root = './Test/Math_notation.pdf'
# output_path = './Test_out/Math_notation_4'

# process_all(name_root, output_path, best_model)