from google import genai
from core.translate_text import *
import os 
import logging
import concurrent.futures
from core.box import Box
# from layout_detection import detect_and_crop_image

logger = logging.getLogger(__name__)

def extract_content_from_single_image(
    box: Box, 
    image_dir: str, 
    api_manager: ApiKeyManager
) -> Box:
    """
    Given a Box (with .coords and .id) and the folder where its cropped image lives,
    upload + run Gemini → fill box.content with the resulting LaTeX string.
    """
    image_path = os.path.join(image_dir, f"cropped_segment_{box.id}_page_{box.page_num}.png")
    client, rate_limiter, key_index = api_manager.get_next_available_model(max_wait_time=60)
    if client is None:
        logger.error(f"No API key available to process {image_path}")
        return box

    try:
        rate_limiter.wait_if_needed(0)
        img_file = client.files.upload(file=image_path)
        logger.info(f"Uploaded image {box.id}: {img_file.name}")

        rate_limiter.wait_if_needed(0)
        prompt = """You are a professional in data creation.
                Extract the content in the image to LaTeX format (including the mathematical notation)

                INSTRUCTIONS: Return the content starting from \begin{document} in LaTeX format, including the mathematical notation."""
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[img_file, prompt],
        )
        raw = resp.text or ""
        # extract only the document body
        start = raw.find(r"\begin{document}")
        end   = raw.find(r"\end{document}") + len(r"\end{document}")
        if 0 <= start < end:
            box.content = raw[start:end]
        else:
            logger.warning(f"Box {box.id}: document markers not found.")
            box.content = raw

    except Exception as e:
        logger.error(f"[Box {box.id}] error: {e}")

    finally:
        api_manager.mark_busy(key_index, False)

    return box


def extract_content_from_multiple_images(
    boxes: List[Box],
    image_dir: str,
    api_manager: ApiKeyManager
) -> List[Box]:
    """
    Given a list of Boxes and the folder of their cropped images, run them all
    in parallel and return back the same list with .content fields populated.
    """
    logger.info(f"Processing {len(boxes)} boxes in {image_dir}")
    enriched: List[Box] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(extract_content_from_single_image, box, image_dir, api_manager)
            for box in boxes
        ]
        for fut in concurrent.futures.as_completed(futures):
            try:
                b = fut.result()
                enriched.append(b)
            except Exception as e:
                logger.error(f"worker error: {e}")

    return enriched
# def main():
#     api_manager = setup_multiple_models()
#     # Iterate through the images in paragraph folder
#     parent_dir = Path("../")
#     image_folder = os.path.join(parent_dir, "paragraph")
#     if not os.path.exists(image_folder):
#         print(f"Image folder {image_folder} does not exist.")
#         return
#     # boxes = detect_and_crop_image(..., ...)
#     pdf_content = extract_content_from_multiple_images(boxes, image_folder, api_manager)
#     print(pdf_content)

# if __name__ == "__main__":
#     main()

    
