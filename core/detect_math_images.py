#!/usr/bin/env python3
import os, glob, argparse, ast
from pathlib import Path
import fitz
import cv2
import torch
from ultralytics import YOLO
from pdf2image import convert_from_path

def pdf_to_jpg_with_sizes(pdf_path: Path, output_folder: Path, dpi=300):
    output_folder.mkdir(exist_ok=True)
    images = convert_from_path(str(pdf_path), dpi=dpi)
    doc = fitz.open(str(pdf_path))
    jpg_size = images[0].size
    pdf_size = (doc[0].rect.width, doc[0].rect.height)
    with open(output_folder/"size.txt","w") as f:
        f.write(f"{jpg_size}\n{pdf_size}\n")
    for i, (img, page) in enumerate(zip(images, doc)):
        img.save(output_folder/f"{i+1}.jpg","JPEG")
    doc.close()

def scale_box_to_pdf(jpg_box, jpg_size, pdf_size):
    jw,jh = jpg_size; pw,ph = pdf_size
    sx,sy = pw/jw, ph/jh
    return [c* (sx if i%2==0 else sy) for i,c in enumerate(jpg_box)]

def generate_pdf_coordinates(image_folder: Path):
    size = image_folder/"size.txt"; idx = image_folder/"index.txt"
    jpg_size, pdf_size = ast.literal_eval(size.read_text().splitlines()[0]), ast.literal_eval(size.read_text().splitlines()[1])
    lines = idx.read_text().splitlines()
    out = []
    for L in lines:
        parts = L.split()
        if len(parts)==5:
            bid, *box = parts; b = scale_box_to_pdf(list(map(float,box)), jpg_size, pdf_size)
            out.append(f"{bid} {b[0]:.4f} {b[1]:.4f} {b[2]:.4f} {b[3]:.4f}")
    (image_folder/"pdf_coor.txt").write_text("\n".join(out))

def crop_and_normalize_all(root_folder: Path):
    images_folder = root_folder/"images"; 
    images_folder.mkdir(exist_ok=True)
    for jpg in root_folder.glob("*.jpg"):
        txt = root_folder/(jpg.stem+".txt")
        if not txt.exists(): continue
        img = cv2.imread(str(jpg)); h,w = img.shape[:2]
        lines = txt.read_text().splitlines()
        norm = []
        for i,L in enumerate(lines):
            parts = L.split()
            if len(parts)==5:
                _,x1,y1,x2,y2 = parts; x1,y1,x2,y2 = map(float,(x1,y1,x2,y2))
                y1,y2 = max(0,y1-5), min(h,y2+5)
                x1,x2 = max(0,x1), min(w,x2)
                crop = img[int(y1):int(y2),int(x1):int(x2)]
                (images_folder/f"{i+1}.jpg").write_bytes(cv2.imencode('.jpg',crop)[1].tobytes())
                norm.append(f"{i+1} {x1:.4f} {y1:.4f} {x2:.4f} {y2:.4f}")
        (root_folder/"index.txt").write_text("\n".join(norm))
        generate_pdf_coordinates(root_folder)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pdf-dir",  required=True, type=Path)
    p.add_argument("--out-dir",  required=True, type=Path)
    p.add_argument("--weights",  default="best.pt")
    p.add_argument("--conf",     type=float, default=0.65)
    p.add_argument("--iou",      type=float, default=0.75)
    args = p.parse_args()
    model = YOLO(str(args.weights))
    for pdf in sorted(args.pdf_dir.glob("*.pdf")):
        fid    = pdf.stem
        folder = args.out_dir/fid
        pdf_to_jpg_with_sizes(pdf, folder)
        preds = model.predict(source=str(folder), conf=args.conf, iou=args.iou, stream=True)
        for batch in preds:
            # write raw .txt
            txt = args.out_dir/fid/"index.txt"
            with open(txt,"w") as f:
                for *box, in batch.boxes.xyxy.cpu().numpy():
                    f.write(" ".join(map(str,box))+"\n")
        crop_and_normalize_all(folder)
        print(f"[detect] done {fid}")

# if __name__=="__main__":
#     main()