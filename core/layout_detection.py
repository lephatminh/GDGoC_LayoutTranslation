from doclayout_yolo import YOLOv10
from huggingface_hub import hf_hub_download
import os
from typing import Dict, List
from PIL import Image
from box import Box


filepath = hf_hub_download(repo_id="juliozhao/DocLayout-YOLO-DocStructBench", filename="doclayout_yolo_docstructbench_imgsz1024.pt")
model = YOLOv10(filepath)

def detect_and_crop_image(image_path: str, output_dir: str) -> List[Box]:
    """
    Detects different regions in the image
    Math equations and paragraphs are cropped and saved in the output_dir
    Input: 
        image_dir: Path to the image of the PDF page
        output_dir: Directory to save the cropped images
    Output: A list of Box objects
    """
    det_res = model.predict(
        f"{image_path}",
        imgsz=1024,
        conf=0.2,
        device="cpu" # or "cuda:0" if you have a GPU
    )
    img = Image.open(image_path)
    boxes = []
    result = det_res[0].boxes
    for i, box in enumerate(result):
        coords = box.xyxy.tolist()[0]
        confidence = box.conf.tolist()[0]
        class_id = int(box.cls.tolist()[0])
        class_name = result.names[class_id]
        if class_id not in [3, 5, 9]:  # Exclude figures, tables, and formula captions
            cropped_img = img.crop(coords)
            output_file = os.path.join(output_dir, f"cropped_segment_{i+1}.png")
            cropped_img.save(output_file)
            boxes.append(Box(
                id = i + 1,
                coords = (coords[0], coords[1], coords[2], coords[3]),
                content = None,
                translation = None,
            ))
    return boxes