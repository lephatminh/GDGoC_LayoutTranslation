from core.box import Box, BoxLabel
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
        # prompt = """You are a LaTeX expert extracting text and mathematical notation from images.

        #         INSTRUCTIONS: Convert the image content into a complete LaTeX document, starting with \begin{document}. Prioritize accurate representation of all mathematical expressions, symbols (including \&, \%, \{, \} etc.), and formatting. Do not include any figure environments (e.g `\begin{figure}...\end{figure}`, '\includegraphics', etc.) or image references. End with \end{document}. Return *only* the LaTeX code, no surrounding text.
        #         """
        # prompt = """You are a LaTeX expert. Your task is to convert image content, which may include multiple languages, into a complete LaTeX document.

        #         **Instructions:**
        #         1.  Begin the output with `\begin{document}`.
        #         2.  End the output with `\end{document}`.
        #         3.  For non-English text, wrap it with the appropriate language command. Do NOT romanize or transliterate; preserve original Unicode characters.
        #             * Vietnamese: `\vi{text}`
        #             * Chinese: `\zh{text}`
        #             * Japanese: `\ja{text}`
        #             * Korean: `\ko{text}`
        #             * Arabic: `\ar{text}`
        #             * Russian: `\ru{text}`
        #             * French: `\fr{text}`
        #             * German: `\de{text}`
        #             * Spanish: `\es{text}`
        #             * Italian: `\ita{text}`
        #             * English: Leave unwrapped.
        #         4.  Prioritize accurate representation of all mathematical expressions, symbols (including \&, \%, \{, \} \&, etc.)
        #         5. Maintain the original formatting as much as possible. Make sure to have a white space after a newline (e.g '\n', etc.). If it's a plain paragraph text, do not add any extra line breaks or spaces.
        #         6.  Do NOT include any figure environments (e.g `\begin{figure}...\end{figure}`, '\includegraphics', etc.) or image references

        #         **Examples:**
        #         * `Hello \vi{xin chào} world`
        #         * `The equation \zh{方程式} is $E=mc^2$`
        #         * `Title: \vi{Toán học} and \zh{数学} and Mathematics`
        #         * `\ja{十}`

        #         **Output ONLY the LaTeX code from `\begin{document}` to `\end{document}`. No other text or explanations.**"""

        prompt = r"""You are an expert at converting specific regions of a document image (identified by a tool like DocLayout) into LaTeX code. Your main job is to carefully change the text, math, and symbols from these document regions into correct LaTeX code that goes between '\begin{document}' and '\end{document}'. You must follow these rules exactly.

        **About the Input Image:**
        The input image you'll work with comes from one of these document parts, like a paragraph, a heading, or a caption. This text might contain various languages, mathematical formulas, and symbols.

        **Main Rules for Creating LaTeX:**

        1.  **Start and End Points:**
            * Your LaTeX code MUST start with '\begin{document}'. Nothing before it.
            * Your LaTeX code MUST end with '\end{document}'. Nothing after it.
            * Only put LaTex code between '\begin{document}' and '\end{document}'. Don't add things like '\documentclass' or '\usepackage'.

        2.  **Handling Different Languages:**
            * For any text that is not English, wrap it with the correct language command (see list below). Keep the original letters and symbols exactly as they are. DO NOT change them to look like English letters (no romanizing or transliterating).
                * Vietnamese: '\vi{text}'
                * Chinese: '\zh{text}'
                * Japanese: '\ja{text}'
                * Korean: '\ko{text}'
                * Arabic: '\ar{text}'
                * Russian: '\ru{text}'
                * French: '\fr{text}'
                * German: '\de{text}'
                * Spanish: '\es{text}'
                * Italian: '\ita{text}'
            * Do not wrap English text with any command.

        3.  **Math and Special Characters:**
            * Change all math into correct LaTeX math. For example, use '$...$' for math in a line of text. The most important thing is to get all symbols right.
            * You MUST put a backslash ('\') before these special LaTeX characters to make them show up correctly:
                * '&' becomes '\&'
                * '%' becomes '\%'
                * '$' becomes '\$'
                * '#' becomes '\#'
                * '_' becomes '\_'
                * '{' becomes '\{'
                * '}' becomes '\}'
                * '~' becomes '\textasciitilde{}'
                * '^' becomes '\textasciicircum{}'
                * '\' (backslash itself) becomes '\textbackslash{}'

        4.  **Keeping the Original Look:**
            * Try your best to make the LaTeX output look like the original document part's layout (like where lines break and paragraphs start).
            * Make sure to have a white space character after a newline (e.g '\n', etc.)
            * For a plain paragraph text, don't add extra new lines or line breaks that weren't meant to be there

        5.  **Things NOT to Include:**
            * DO NOT use '\begin{figure}' or '\end{figure}'.
            * DO NOT use '\includegraphics'.
            * Don't refer to image files or try to put images in.

        **Examples (Follow these carefully):**

        * Input: 'Hello xin chào world'
            Output: 'Hello \vi{xin chào} world'

        * Input: 'The equation 方程式 is E=mc^2'
            Output: 'The equation \zh{方程式} is $E=mc^2$'

        * Input: 'Title: Toán học and 数学 and Mathematics. Cost is 100% & item #1 {special_item}.'
            Output: 'Title: \vi{Toán học} and \zh{数学} and Mathematics. Cost is 100\% \& item \#1 \{special\_item\}.'

        * Input: '十'
            Output: '\ja{十}'

        **Very Important Last Rule:**
        Give back ONLY the LaTeX code that starts with '\begin{document}' and ends with '\end{document}'. Don't say anything else before or after it.
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
            # grab the body, normalize newlines for titles, then strip
            segment = raw[start:end].strip()
            if box.label == BoxLabel.TITLE:
                segment = segment.replace("\n", " ")
            elif (not r'\begin{verbatim}' in segment or not r'\end{verbatim}' in segment):
                # if no verbatim, replace newlines with \\
                segment = segment.replace("\n", r"\\")

            box.content = segment.strip()

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