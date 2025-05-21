import os
from google import genai
from google.genai import types
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
import threading
import concurrent.futures
from typing import List, Dict, Any
from pathlib import Path
from tqdm import tqdm
from dotenv import load_dotenv
from core.extract_contexts import *
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
current_dir = Path(__file__).parent


class GeminiModel(Enum):
    GEMINI_PRO = "gemini-pro"
    GEMINI_1_5_FLASH = "gemini-1.5-flash-latest"
    GEMINI_1_5_PRO = "gemini-1.5-pro-latest"
    GEMINI_2_FLASH = "gemini-2.0-flash"
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
            return cls(model, 4000, 400000, 4_000_000)
        else:
            raise ValueError(f"Unsupported model: {model}")

class ApiKeyManager:
    def __init__(self):
        self.models = []
        self.rate_limiters = []
        self.lock = threading.RLock()
        self.available_keys = []  # Track which keys are currently available
        self.worker_counts = []   # Track how many workers are using each key
        self.wait_condition = threading.Condition(self.lock)  # For waiting on API availability

    def add_model(self, model, rate_limiter):
        """Add a model with its own rate limiter"""
        with self.lock:
            self.models.append(model)
            self.rate_limiters.append(rate_limiter)
            self.available_keys.append(True)
            self.worker_counts.append(0)

    def get_next_available_model(self, max_wait_time=30):
        """
        Get the next available model and its associated rate limiter.
        Will wait up to max_wait_time seconds if no model is available.

        Args:
            max_wait_time: Maximum time to wait in seconds for an available API

        Returns:
            tuple: (model, rate_limiter, index) or (None, None, -1) if wait timed out
        """
        start_time = time.time()
        with self.lock:
            while (time.time() - start_time) < max_wait_time:
                # First try to find a completely unused API
                for i, available in enumerate(self.available_keys):
                    if available and self.worker_counts[i] == 0:
                        self.worker_counts[i] += 1
                        return self.models[i], self.rate_limiters[i], i

                # If no unused API, find the one with fewest workers (load balancing)
                min_workers = float('inf')
                min_index = -1

                for i, available in enumerate(self.available_keys):
                    if available and self.worker_counts[i] < min_workers:
                        min_workers = self.worker_counts[i]
                        min_index = i

                if min_index >= 0:
                    self.worker_counts[min_index] += 1
                    return self.models[min_index], self.rate_limiters[min_index], min_index

                # If we get here, no API is available, wait for notification
                logger.info("No API available, waiting...")
                self.wait_condition.wait(timeout=1.0)  # Wait with timeout to recheck periodically

            # If we get here, we timed out waiting for an API
            logger.warning(f"Timed out after {max_wait_time}s waiting for API availability")
            return None, None, -1

    def mark_busy(self, index, busy=True):
        """Mark a model as busy or available"""
        with self.lock:
            if 0 <= index < len(self.available_keys):
                self.available_keys[index] = not busy

                if not busy:  # Model becoming available
                    self.worker_counts[index] = max(0, self.worker_counts[index] - 1)  # Decrement worker count
                    self.wait_condition.notify_all()  # Notify waiting threads

    def size(self):
        """Return the number of models"""
        return len(self.models)

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
    client = genai.Client(api_key=api_key)
    return client

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
    api_manager = ApiKeyManager()

    for i in range(1, 8):
        j = i % 3 # Currently have 3 API keys
        api_key = os.getenv(f"{default_api_str}_{j}")
        if not api_key:
            logger.warning(f"API key {default_api_str}_{j} not found, skipping.")
            continue
        try:
            model = setup_gemini(api_key)
            rate_limiter = GeminiRateLimiter()  # Create individual rate limiter for each API
            api_manager.add_model(model, rate_limiter)
            logger.info(f"Model {i} setup successfully.")
        except Exception as e:
            logger.error(f"Failed to setup model {i}: {str(e)}")
            continue

    return api_manager

def translate_with_gemini(model, text, rate_limiter, context):
    """Translate text using Gemini model with comprehensive rate limiting"""
    # source_lang = "English"
    target_lang = "Vietnamese"
    try:
        # Estimate tokens (roughly 4 chars per token for Vietnamese/English)
        estimated_tokens = len(text) // 4 * 2  # Input + output tokens
        # Wait if we're approaching rate limits
        rate_limiter.wait_if_needed(estimated_tokens)

        prompt = f"""TRANSLATION TASK

        TARGET LANGUAGE: {target_lang}

        INSTRUCTIONS:
        1.  Carefully review the <CONTEXT> provided below to understand the subject matter, specific terminology, and desired tone.
        2.  Translate ONLY the text enclosed within the <TEXT_TO_TRANSLATE>...</TEXT_TO_TRANSLATE> tags to {target_lang}.
        3.  Provide ONE single, accurate, and formal translation in {target_lang}.
        4.  Preserve ALL original formatting. This includes paragraphs, line breaks, bullet points, numbering, bolding, italics, and any HTML tags present *within* the source text to be translated.
        5.  Maintain the exact hierarchical structure and layout of the original text within <TEXT_TO_TRANSLATE>.
        6.  Use the <CONTEXT> information to ensure semantic accuracy and consistency with any established terminology or style.
        7.  Output ONLY the translated text. Do NOT include any preambles, apologies, explanations, alternative translations, or any text other than the direct translation itself.
        8.  If the <TEXT_TO_TRANSLATE> section is empty or contains only whitespace, output the original text.

        <CONTEXT>
        {context}
        </CONTEXT>

        <TEXT_TO_TRANSLATE>
        {text}
        </TEXT_TO_TRANSLATE>

        Translation:"""

        generation_config = {
            "temperature": 0.05,  # Lowered for more deterministic output
            "top_p": 0.85,
            "top_k": 45,
            "max_output_tokens": 1024,
            "stop_sequences": ["\n\n"]
        }
        safety_settings = {
            "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
            "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
            "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE"
        }

        response = model.models.generate_content(
            model=MODEL,
            contents=[prompt],
            config=types.GenerateContentConfig(
                max_output_tokens=generation_config["max_output_tokens"],
                temperature=generation_config["temperature"],
                top_p=generation_config["top_p"],
                top_k=generation_config.get("top_k"),
                stop_sequences=generation_config["stop_sequences"]
            )
        )

        if response and response.text:
            return response.text.strip()
        return None
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        raise

def translate_box(args):
    """
    Translate a single text box using the API manager.
    """
    box, api_manager, pdfpig_boxes = args
    source_text = box["text"]
    x_coord = box["x"]
    y_coord = box["y"]
    width = box["width"]
    height = box["height"]

    original_box = {
        "x": x_coord,
        "y": y_coord,
        "width": width,
        "height": height,
        "text": source_text
    }

    if not source_text or len(source_text.strip()) == 0:
        return {**original_box, "text_vi": ""}

    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Get context for this box
            context = get_contexts(box, pdfpig_boxes)
            context = " ".join(context) if context else "No context available"

            # Get an available model with a timeout
            model, rate_limiter, model_index = api_manager.get_next_available_model(max_wait_time=60)
            if model is None:
                # No model available even after waiting, retry
                retry_count += 1
                if retry_count < max_retries:
                    logger.warning(f"No API available, retrying ({retry_count}/{max_retries})...")
                    time.sleep(5)  # Wait a bit before retrying
                    continue
                else:
                    return {**original_box, "text_vi": "[TRANSLATION UNAVAILABLE - NO API]"}

            try:
                # No need to mark busy, already handled by get_next_available_model

                # Translate the text
                translated_text = translate_with_gemini(model, source_text, rate_limiter, context)
                return {**original_box, "text_vi": translated_text or ""}
            finally:
                # Release the model when done
                api_manager.mark_busy(model_index, busy=False)

            # If we got here, translation was successful
            break

        except Exception as e:
            logger.error(f"Translation error for box: {str(e)}")
            retry_count += 1
            time.sleep(2)  # Brief wait before retry

    # If we exhausted all retries
    return {**original_box, "text_vi": ""}

def translate_document(pymuboxes: List[Dict[str, Any]], api_manager, pdfpig_boxes) -> List[Dict[str, Any]]:
    """
    Translate document text boxes in parallel using multiple API keys with individual rate limiters.

    Args:
        pymuboxes: List of text boxes to translate
        api_manager: API manager instance with models and rate limiters
    """
    if not pymuboxes:
        logger.warning("No boxes to translate")
        return []

    # Create tasks with API manager
    tasks = [(box, api_manager, pdfpig_boxes) for box in pymuboxes]

    results = []

    # Use 8 workers as specified by the user, regardless of API count
    num_workers = 8

    logger.info(f"Starting translation with {num_workers} workers and {api_manager.size()} APIs")

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = list(tqdm(
            executor.map(translate_box, tasks),
            total=len(tasks),
            desc="Translating boxes"
        ))

        results = futures

    return results