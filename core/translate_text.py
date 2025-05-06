import time
import logging
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
from collections import deque
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)
import google.api_core.exceptions
import json
from typing import Dict, List, Any
from google import genai
import os
from dotenv import load_dotenv
from csv_utils import *
import csv
from pathlib import Path
from detect_context import *
load_dotenv()
import threading
import concurrent.futures
from queue import Queue
from tqdm import tqdm


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
current_dir = Path(__file__).parent


class GeminiModel(Enum):
    GEMINI_PRO = "gemini-pro"
    GEMINI_1_5_FLASH = "gemini-1.5-flash-latest"
    GEMINI_1_5_PRO = "gemini-1.5-pro-latest"
    GEMINI_2_FLASH = "gemini-2.0-flash-exp"
    GEMINI_2_FLASH_LITE = "gemini-2.0-flash-lite"
    GEMINI_1_5_PRO_002 = "gemini-1.5-pro-002"\
    
@dataclass
class ModelConfig:
    model: GeminiModel
    rpm_limit: int
    rpd_limit: int
    tpm_limit: int

    @classmethod
    def get_config(cls, model: GeminiModel):
        if model == GeminiModel.GEMINI_PRO:
            return cls(model, 15, 1_500, 1_000_000)
        elif model == GeminiModel.GEMINI_1_5_FLASH:
            return cls(model, 15, 1_500, 1_000_000)
        elif model == GeminiModel.GEMINI_1_5_PRO:
            return cls(model, 2, 50, 32_000)
        elif model == GeminiModel.GEMINI_2_FLASH:
            return cls(model, 10, 1_500, 1_000_000)
        elif model == GeminiModel.GEMINI_1_5_PRO_002:
            return cls(model, 6, 1_500, 1_000_000)
        elif model == GeminiModel.GEMINI_2_FLASH_LITE:
            return cls(model, 30, 1_500, 1_000_000)
        else:
            raise ValueError(f"Unsupported model: {model}")
        

CURRENT_CONFIG = ModelConfig.get_config(GeminiModel.GEMINI_2_FLASH_LITE)
MODEL = CURRENT_CONFIG.model.value
RPM_LIMIT = CURRENT_CONFIG.rpm_limit
RPD_LIMIT = CURRENT_CONFIG.rpd_limit
TPM_LIMIT = CURRENT_CONFIG.tpm_limit

class GeminiRateLimiter:
    def __init__(self):
        # Queue length matches time window
        self.minute_requests = deque(maxlen=RPM_LIMIT)
        self.daily_requests = deque(maxlen=RPD_LIMIT)
        self.minute_tokens = deque(maxlen=TPM_LIMIT)

        # Track current window start times
        self.last_cleanup = datetime.now()
        
    def _clean_old_requests(self):
        """Remove outdated entries to maintain sliding window limits."""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        day_ago = now - timedelta(days = 1)
        
        # Remove requests older than 1 minute
        while self.minute_requests and self.minute_requests[0] <= minute_ago:
            self.minute_requests.popleft()
        
        # Remove tokens older than 1 minute
        while self.minute_tokens and self.minute_tokens[0][0] <= minute_ago:
            self.minute_tokens.popleft()
            
        # Remove requests older than 1 day
        while self.daily_requests and self.daily_requests[0] <= day_ago:
            self.daily_requests.popleft()

        self.last_cleanup = now
    
    def _calculate_sleep_time(self, deque_list, time_delta) -> float:
        """Calculate the sleep time to respect rate limits."""
        if not deque_list:
            return 0

        now = datetime.now()
        if len(deque_list) >= deque_list.maxlen:
            sleep_time = (deque_list[0] + time_delta - now).total_seconds()
            return max(0, sleep_time)
        return 0

    def _wait_if_exceeded(self, condition, sleep_time, limit_type):
        """Pause execution if a rate limit is exceeded."""
        if condition and sleep_time > 0:
            logger.warning(f"{limit_type} limit reached. Sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
    
    def wait_if_needed(self, estimated_tokens=1000):
        """
        Check all rate limits and wait if necessary.
        Args:
            estimated_tokens: Estimated token count for this request
        """
        # Only clean if significant time has passed (e.g., every 5 seconds)
        now = datetime.now()
        if (now - self.last_cleanup).total_seconds() > 5:
            self._clean_old_requests()
        
        # Check RPM limit
        rpm_sleep_time = self._calculate_sleep_time(self.minute_requests, timedelta(minutes=1))
        self._wait_if_exceeded(len(self.minute_requests) >= RPM_LIMIT, rpm_sleep_time, "RPM")
        
        # Check RPD limit
        rpd_sleep_time = self._calculate_sleep_time(self.daily_requests, timedelta(days=1))
        self._wait_if_exceeded(len(self.daily_requests) >= RPD_LIMIT, rpd_sleep_time, "RPD")
        
        # Check TPM limit
        current_tokens = sum(tokens for _, tokens in self.minute_tokens)
        tpm_sleep_time = self._calculate_sleep_time(self.minute_tokens, timedelta(minutes=1))
        self._wait_if_exceeded(
            current_tokens + estimated_tokens > TPM_LIMIT, tpm_sleep_time, "TPM"
        )
        
        # Record new request and tokens
        now = datetime.now()
        self.minute_requests.append(now)
        self.daily_requests.append(now)
        self.minute_tokens.append((now, estimated_tokens))
        
        # Debugging logs
        logger.info(
            f"Current: {len(self.minute_requests)} RPM, {len(self.daily_requests)} RPD, {current_tokens} Tokens/Min"
        )

def setup_gemini(api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL)
    return model

@retry(
    retry=retry_if_exception_type((
        google.api_core.exceptions.ResourceExhausted,
        google.api_core.exceptions.ServiceUnavailable,
        google.api_core.exceptions.TooManyRequests
    )),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    stop=stop_after_attempt(5),
    before_sleep=before_sleep_log(logger, logging.INFO),
    after=after_log(logger, logging.INFO)
)

def setup_multiple_models():
    """Setup multiple models with different configurations"""
    default_api_str = "GEMINI_API_KEY"
    models = []
    for i in range(1,14):
        api_key = os.getenv(f"{default_api_str}_{i}")
        if not api_key:
            logger.warning(f"API key {default_api_str}_{i} not found, skipping.")
            continue
        try:
            model = setup_gemini(api_key)
            logger.info(f"Model {i} setup successfully.")
        except Exception as e:
            logger.error(f"Failed to setup model {i}: {str(e)}")
            continue
        models.append(model)
    return models

def translate_with_gemini(model, text, rate_limiter, context):
    """Translate text using Gemini model with comprehensive rate limiting"""
    source_lang = "English"
    target_lang = "Vietnamese"
    try:
        # Estimate tokens (roughly 4 chars per token for Vietnamese/English)
        estimated_tokens = len(text) // 4 * 2  # Input + output tokens
        
        # Wait if we're approaching rate limits
        rate_limiter.wait_if_needed(estimated_tokens)

        prompt = f"""Translate this {source_lang} text to formal {target_lang}.
        Instructions:
        - Provide exactly ONE translation
        - Keep the original meaning and cultural context
        - Use formal, elegant English
        - Do not provide multiple versions or alternatives
        - Do not include explanatory text
        - Preserve the translation order according to the context given below.
        - Do not add any additional content in the context or drop any content from the source
        
        Context: {context}
        Source {source_lang} text:
        {text}
        Translate to {target_lang}:
        """
        
        generation_config = {
            "temperature": 0.3,
            "top_p": 0.85,
            "top_k": 40,
            "max_output_tokens": 1024,
            "stop_sequences": ["\n\n"]
        }

        safety_settings = {
            "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
            "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
            "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE"
        }

        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        if response and response.text:
            return response.text.strip()
        return None
    
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        raise
def translate_box(args):
    """
    Translate a single text box using the specified model.
    This function is designed to be used with ThreadPoolExecutor.
    """
    box, model, rate_limiter, pdfpig_boxes = args
    source_text = box["text"]
    
    if not source_text or len(source_text.strip()) == 0:
        return {**box, "translated_text": ""}
    
    try:
        # Get context for this box
        context = get_contexts(box, pdfpig_boxes)
        context = " ".join(context) if context else "Document translation"
        
        # Translate the text
        translated_text = translate_with_gemini(model, source_text, rate_limiter, context)
        return {**box, "translated_text": translated_text or ""}
    except Exception as e:
        logger.error(f"Translation error for box ID {box.get('id', 'unknown')}: {str(e)}")
        return {**box, "translated_text": ""}
    
def translate_document(pymuboxes: List[Dict[str, Any]], models, rate_limiter) -> List[Dict[str, Any]]:
    """
    Translate document text boxes in parallel using multiple API keys.
    Uses ThreadPoolExecutor to process multiple boxes concurrently.
    
    Args:
        pymuboxes: List of text boxes to translate
        models: List of initialized Gemini models
        rate_limiter: Rate limiter instance to manage API quotas
        
    Returns:
        List of dictionaries containing original boxes with added translations
    """
    if not pymuboxes:
        logger.warning("No boxes to translate")
        return []

    csv_path = current_dir.parent / "submission_pdfpig.csv"
    pdfpig_boxes = load_csv_data_pdfpig(csv_path)
    pdfpig_boxes = pdfpig_boxes["cfb267ee38361a88917d5c2cc80dc4524cede67df47b54ec7df07952e6f57eb2"]
    
    # Create a thread lock for the rate limiter to prevent race conditions
    rate_limiter_lock = threading.RLock()
    
    # Modify rate limiter to be thread-safe
    original_wait_if_needed = rate_limiter.wait_if_needed
    def thread_safe_wait_if_needed(estimated_tokens=1000):
        with rate_limiter_lock:
            return original_wait_if_needed(estimated_tokens)
    rate_limiter.wait_if_needed = thread_safe_wait_if_needed
    

    tasks = []
    model_count = len(models)
    for i, box in enumerate(pymuboxes):
        # Round-robin distribution of models
        model_index = i % model_count
        tasks.append((box, models[model_index], rate_limiter, pdfpig_boxes))
    
    results = []
    max_workers = min(6, model_count)  # Set maximum number of concurrent threads
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = list(tqdm(
            executor.map(translate_box, tasks), 
            total=len(tasks),
            desc="Translating boxes"
        ))
        
        results = futures
    
    return results
        
    
def main():
    rate_limiter = GeminiRateLimiter()
    models = setup_multiple_models()
    # Load PyMuPDF boxes
    pymuboxes = load_csv_data_pymupdf(current_dir.parent / "submission_ocr_official.csv")
    doc_id = "cfb267ee38361a88917d5c2cc80dc4524cede67df47b54ec7df07952e6f57eb2"
    pymuboxes = pymuboxes[doc_id]
    
    # Translate document
    translated_boxes = translate_document(pymuboxes, models, rate_limiter)
    # Save results to CSV
    output_path = current_dir.parent / "translated_boxes.csv"

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = translated_boxes[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for box in translated_boxes:
            writer.writerow(box)
    logger.info(f"Translation completed. Results saved to {output_path}")

if __name__ == "__main__":
    main()