from doclayout_yolo import YOLOv10
from huggingface_hub import hf_hub_download
import os
from typing import Dict, List
from PIL import Image

filepath = hf_hub_download(repo_id="juliozhao/DocLayout-YOLO-DocStructBench", filename="doclayout_yolo_docstructbench_imgsz1024.pt")
model = YOLOv10(filepath)

def detect_and_crop_image(image_path: str, output_dir: str):
    """
    Detects different regions in the image
    Math equations and paragraphs are cropped and saved in the output_dir
    Input: 
        image_dir: Path to the image of the PDF page
        output_dir: Directory to save the cropped images
    """
    det_res = model.predict(
        f"{image_path}",
        imgsz=1024,
        conf=0.2,
        device="cpu" # or "cuda:0" if you have a GPU
    )
    img = Image.open(image_path)
    results = det_res[0]
    boxes = results.boxes
    for i, box in enumerate(boxes):
        coords = box.xyxy.tolist()[0]
        confidence = box.conf.tolist()[0]
        class_id = int(box.cls.tolist()[0])
        class_name = results.names[class_id]
        if class_id not in [3, 5, 8, 9]:
            cropped_img = img.crop(coords)
            output_file = os.path.join(output_dir, f"cropped_segment_{i+1}.png")
            cropped_img.save(output_file)
        print(f"Box: {coords}, Confidence: {confidence:.2f}, Class ID: {class_id}, Class Name: {class_name}")
        
