from core.box import Box
from core.api_manager import ApiKeyManager
from typing import List
from core.preprocess_text import normalize_spaced_text, clean_text
import os 
import logging
import concurrent.futures
import fitz


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
    if box.label == 5: # Skip table
        logger.info(f"Skipping table box {box.id}")
        return box

    try:
        rate_limiter.wait_if_needed(0)
        img_file = client.files.upload(file=image_path)
        logger.info(f"Uploaded image {box.id}: {img_file.name}")

        rate_limiter.wait_if_needed(0)
        prompt = """You are a LaTeX expert extracting text and mathematical notation from images.

                INSTRUCTIONS: Convert the image content into a complete LaTeX document, starting with \begin{document}. Prioritize accurate representation of all mathematical expressions, symbols (including \&, \%, etc.), and formatting. Do not include any figure environments (e.g `\begin{figure}...\end{figure}`, '\includegraphics', etc.) or image references. End with \end{document}. Return *only* the LaTeX code, no surrounding text.
                """
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[img_file, prompt],
        )
        raw = resp.text or ""
        # extract only the document body
        start = raw.find(r"\begin{document}") + len(r"\begin{document}")
        end   = raw.find(r"\end{document}")
        if 0 <= start < end:
            box.content = raw[start:end].strip().replace('\n', '')

        else:
            logger.warning(f"Box {box.id}: document markers not found.")
            box.content = raw

    except Exception as e:
        logger.error(f"[Box {box.id}] error: {e}")

    finally:
        api_manager.mark_busy(key_index, False)

    return box


# def extract_content_from_multiple_images(
#     boxes: List[Box],
#     image_dir: str,
#     api_manager: ApiKeyManager
# ) -> List[Box]:
#     """
#     Given a list of Boxes and the folder of their cropped images, run them all
#     in parallel and return back the same list with .content fields populated.
#     """
#     logger.info(f"Processing {len(boxes)} boxes in {image_dir}")
#     enriched: List[Box] = []

#     with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
#         futures = [
#             executor.submit(extract_content_from_single_image, box, image_dir, api_manager)
#             for box in boxes
#         ]
#         for fut in concurrent.futures.as_completed(futures):
#             try:
#                 b = fut.result()
#                 enriched.append(b)
#             except Exception as e:
#                 logger.error(f"worker error: {e}")

#     return enriched


def get_content_in_region(doc: fitz.Document, boxes: List[Box]) -> List[Box]:
    '''
    Extract content in the region (top_left and bottom_right) of a PDF, including text and image metadata.

    Args:
        pdf: Path to the PDF
        x_left: X-coordinate of the top-left corner
        y_left: Y-coordinate of the top-left corner
        x_right: X-coordinate of the bottom-right corner
        y_right: Y-coordinate of the bottom-right corner

    Return:
        List of Boxes containing text and image metadata
        [Box(
            id: set to -1
            label: set to -1
            coords: Tuple(x_left, y_left, x_right, y_right) - from OCR or image bounds
            content: str - text or image metadata
            translation: str - same as content
            page_num: 0
        )]
    '''
    results: List[Box] = []
    for box in boxes:
        page = doc[box.page_num]
        x0, y0, x1, y1 = box.coords
        rect = fitz.Rect(x0, y0, x1, y1)

        # pull out all text spans in this region
        for block in page.get_text("dict", clip=rect)["blocks"]:
            if block["type"] == 0:
                for line in block["lines"]:
                    for span in line["spans"]:
                        sx0, sy0, sx1, sy1 = span["bbox"]
                        # simple overlap test
                        span["text"] = span["text"].strip()
                        
                        if not span["text"]:
                            continue

                        content = clean_text(span["text"])
                        content = normalize_spaced_text(content)
                        results.append(Box(
                            id=-1,
                            label=box.label,
                            coords=(sx0, sy0, sx1, sy1),
                            content=content,
                            translation=content,
                            page_num=box.page_num
                        ))
        
    return results