import time
import logging
from typing import Dict, List, Any
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
# from csv_utils import *
import csv
from pathlib import Path
from extract_contexts import *
load_dotenv()
import concurrent.futures
from tqdm import tqdm
from api_manager import *
from box import Box


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
current_dir = Path(__file__).parent


def translate_with_gemini(model, text, rate_limiter):
    """Translate text using Gemini model with comprehensive rate limiting"""

    target_lang = "Vietnamese"
    try:
        # Estimate tokens (roughly 4 chars per token for Vietnamese/English)
        estimated_tokens = len(text) // 4 * 2  # Input + output tokens
        # Wait if we're approaching rate limits
        rate_limiter.wait_if_needed(estimated_tokens)
        
        prompt = f"""TRANSLATION TASK

        TARGET LANGUAGE: {target_lang}

        INSTRUCTIONS:
        1.  Translate ONLY the text enclosed within the <TEXT_TO_TRANSLATE>...</TEXT_TO_TRANSLATE> tags to {target_lang}.
        2.  Provide ONE single, accurate, and formal translation in {target_lang}.
        3.  Preserve ALL original formatting. This includes inline math latex (enclosed by $$), bullet points, numbering, bolding, italics, underscore, monospace font
        4.  Maintain the exact hierarchical structure and layout of the original text within <TEXT_TO_TRANSLATE>.
        5.  Output ONLY the translated text. Do NOT include any preambles, apologies, explanations, alternative translations, or any text other than the direct translation itself.
        6.  If the <TEXT_TO_TRANSLATE> section is empty or contains only whitespace, output the original text.


        <TEXT_TO_TRANSLATE>
        {text}
        </TEXT_TO_TRANSLATE>

        Translation:"""

        generation_config = {
            "temperature": 0.15,
            "top_p": 0.85,
            "top_k": 40,
            "max_output_tokens": 1024,
            "stop_sequences": ["\n\n"]
        }

        response = model.models.generate_content(
            model=MODEL,
            contents=[prompt],
            config = types.GenerateContentConfig(
                max_output_tokens=generation_config["max_output_tokens"],
                temperature=generation_config["temperature"],
                top_p=generation_config["top_p"],
                top_k=generation_config["top_k"],
                stop_sequences=generation_config["stop_sequences"],
            )
        )
        
        if response and response.text:
            return response.text.strip()
        return None
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        raise

def translate_single_box(box: Box, api_manager: ApiKeyManager) -> Box:
    """
    Worker that grabs a model slot, translates box.content,
    fills box.translation, then releases the slot.
    """
    client, rate_limiter, key_idx = api_manager.get_next_available_model(max_wait_time=60)
    if client is None:
        logger.error(f"No API key available to translate box {box.id}")
        return box

    try:
        # call your existing translate function
        translation = translate_with_gemini(client, box.content or "", rate_limiter)
        box.translation = translation
    except Exception as e:
        logger.error(f"[Box {box.id}] translation error: {e}")
    finally:
        api_manager.mark_busy(key_idx, False)

    return box
    
def translate_document(
    boxes: List[Box],
    api_manager: ApiKeyManager,
    max_workers: int = 6
) -> List[Box]:
    """
    Translate a list of Box objects in parallel.
    Each Box.content → Box.translation via Gemini.
    """
    if not boxes:
        return []

    translated: List[Box] = []
    logger.info(f"Translating {len(boxes)} boxes with {max_workers} workers")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_box = {
            executor.submit(translate_single_box, box, api_manager): box
            for box in boxes
        }
        for future in tqdm(
            concurrent.futures.as_completed(future_to_box),
            total=len(future_to_box),
            desc="Translating"
        ):
            box = future_to_box[future]
            try:
                result = future.result()
                translated.append(result)
            except Exception as e:
                logger.error(f"Future error for box {box.id}: {e}")

    return translated