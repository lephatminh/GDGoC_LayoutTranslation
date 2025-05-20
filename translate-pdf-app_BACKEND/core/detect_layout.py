from doclayout_yolo import YOLOv10
from huggingface_hub import hf_hub_download
from typing import List
from PIL import Image
from core.box import *
from functools import lru_cache
import os

@lru_cache(maxsize=1)
def get_model() -> YOLOv10:
    """
    Download the YOLOv10 model from Hugging Face Hub and return the model instance.
    """
    """
    Lazily download & initialize the YOLOv10 model, then cache it.
    """
    model_file = hf_hub_download(
        repo_id="juliozhao/DocLayout-YOLO-DocStructBench",
        filename="doclayout_yolo_docstructbench_imgsz1024.pt"
    )
    return YOLOv10(model_file)

def detect_and_crop_image(image_path: str, output_dir: str, page_num: int, model: YOLOv10) -> List[Box]:
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
    boxes: List[Box] = []
    result = det_res[0].boxes
    for i, box in enumerate(result):
        coords = box.xyxy.tolist()[0]
        class_id = int(box.cls.tolist()[0])
        if class_id not in [2, 3, 5, 9]:  # Exclude figures, tables, formula captions, and those abandoned :)
            cropped_img = img.crop(coords)
            output_file = os.path.join(output_dir, f"cropped_segment_{i}_page_{page_num}.png")
            cropped_img.save(output_file)
            boxes.append(Box(
                id = i,
                label = class_id,
                coords = (coords[0], coords[1], coords[2], coords[3]),
                content = None,
                translation = None,
                page_num=page_num,
            ))
    return boxes