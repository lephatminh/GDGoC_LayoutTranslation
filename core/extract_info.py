from google import genai
from translate_text import *
import os 
import logging
import concurrent.futures

logger = logging.getLogger(__name__)

def extract_content_from_single_image(image_path: str, api_manager) -> str:
    """
    Extract paragraphs (including inline math) and isolate math equations from the image to LaTeX format
    Input: Path to the cropped image
    Output: LaTeX format of the content of a single image
    """
    
    client, rate_limiter, key_index = api_manager.get_next_available_model(max_wait_time=60)
    content = None
    if client is None:
        logger.error(f"No API key available to process {image_path}")
        return None

    try:
        rate_limiter.wait_if_needed(0)
        try:
            image_file = client.files.upload(file=image_path)
            logger.info(f"Image file uploaded: {image_file}")
        except Exception as e:
            logger.error(f"Error uploading image file: {e}")
            exit() # Example: exit if upload fails


        prompt_text = """You are a professional in data creation.
                Extract the content in the image to LaTeX format (including the mathematical notation)

                INSTRUCTIONS: Return the content starting from \begin{document} in LaTeX format, including the mathematical notation."""

        try:
            rate_limiter.wait_if_needed(0)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[image_file, prompt_text],
            )

            content = response.text

        except Exception as e:
            logger.error(f"Error generating content: {e}")
    finally:
        api_manager.mark_busy(key_index, False)
    
    return content

def extract_content_from_multiple_images(image_dir: str, api_manager) -> List[str]:
    """
    Extract paragraphs (including inline math) and isolate math equations from the images to LaTeX format
    Using multithreading to process multiple images concurrently
    Input: Path to the folder containing cropped images
    Output: LaTeX format of the content
    """

    image_files = [os.path.join(image_dir, f) for f in os.listdir(image_dir) if os.path.isfile(os.path.join(image_dir, f))]
    print(f"Found {len(image_files)} images in {image_dir}")
    content_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for image_file in image_files:
            futures.append(executor.submit(extract_content_from_single_image, image_file, api_manager))

        for future in concurrent.futures.as_completed(futures):
            try:
                content = future.result()
                if content:
                    content_list.append(content)
            except Exception as e:
                logger.error(f"Error processing image: {e}")
    return content_list


def main():
    api_manager = setup_multiple_models()
    # Iterate through the images in paragraph folder
    parent_dir = Path("../")
    image_folder = os.path.join(parent_dir, "paragraph")
    if not os.path.exists(image_folder):
        print(f"Image folder {image_folder} does not exist.")
        return
    pdf_content = extract_content_from_multiple_images(image_folder, api_manager)
    print(pdf_content)

if __name__ == "__main__":
    main()

    
