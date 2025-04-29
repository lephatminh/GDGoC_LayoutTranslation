from deep_translator import GoogleTranslator
from langdetect import detect, DetectorFactory
import logging
import time


# Add after the other initialization code
DetectorFactory.seed = 0  # For reproducibility


def map_language_code_for_deep_translator(lang_code):
    mapping = {
        "zh-cn": "zh-CN",
        "zh-hans": "zh-CN",
        "zh-tw": "zh-TW",
        'zh-hant': 'zh-TW',
        'zh': 'zh-CN',     # Default Chinese to Simplified
        'jw': 'jv',        # Javanese
        'iw': 'he',        # Hebrew
        'in': 'id',        # Indonesian
        'ceb': 'tl',       # Adjust Cebuano to use Tagalog
    }

    return mapping.get(lang_code, lang_code)


def batch_translate_text(texts_with_langs, target='vi', batch_size=25, delay=0):
    """
    Translate a batch of texts with rate limiting.
    
    Args:
        texts: List of texts to translate
        source: Source language code
        target: Target language code
        batch_size: Number of texts to translate in one batch
        delay: Delay between batches in seconds
        
    Returns:
        List of translated texts
    """
    results = [""] * len(texts_with_langs)

    # Group text by detected source language
    lang_groups = {}
    for text, lang, orig_idx in texts_with_langs:
        if not lang in lang_groups:
            lang_groups[lang] = []
        lang_groups[lang].append((text, orig_idx))

    for source_lang, texts_with_indices in lang_groups.items():
        if source_lang == target:
            for text, orig_idx in texts_with_indices:
                results[orig_idx] = text
            continue

        texts = [t[0] for t in texts_with_indices]
        indices = [t[1] for t in texts_with_indices]

        # Create translator for this language
        translator = GoogleTranslator(source=source_lang, target=target)

        translated_batch = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:min(i + batch_size, len(texts))]
            
            # Process each text in the current batch
            batch_results = []
            for text in batch:
                try:    
                    translated = translator.translate(text)
                    batch_results.append(translated)
                    
                except Exception as e:
                    logging.warning(f"Translation error: {str(e)[:100]}...")
                    # Return original text on error
                    batch_results.append(text)
                    
                    # Handle rate limiting - increase delay and reduce batch size
                    if "429" in str(e) or "too many requests" in str(e).lower():
                        logging.info(f"Rate limit hit. Increasing delay to {delay*2}s and reducing batch size.")
                        delay *= 2
                        batch_size = max(1, batch_size // 2)
                        time.sleep(5)  # Additional pause after hitting rate limit
            
            translated_batch.extend(batch_results)
            
            # Add delay between batches
            if i + batch_size < len(texts):
                time.sleep(delay)

        # Put translated texts back in their original positions
        for translated_text, orig_idx in zip(translated_batch, indices):
            results[orig_idx] = translated_text
            
    return results


def translate_cells(cells, target='vi'):
    """
    Translate text in cells from source language to target language.
    
    Args:
        cells: List of cell dictionaries with text
        source: Source language code
        target: Target language code
        
    Returns:
        List of cell dictionaries with translated text
    """
    # Extract all texts and detect languages
    texts_with_langs = []
    for i, cell in enumerate(cells):
        if cell.get("text"):
            try:
                # Detect language for each text
                lang = detect(cell["text"])
                # Map language code for deep_translator
                mapped_lang = map_language_code_for_deep_translator(lang)
                # Store original language in cell
                texts_with_langs.append((cell["text"], mapped_lang, i))
            except Exception as e:
                logging.warning(f"Language detection error: {str(e)[:100]}... Using 'en' as fallback.")
                texts_with_langs.append((cell["text"], "en", i))
    
    logging.info(f"Translating {len(texts_with_langs)} text segments to {target}...")

    lang_counts = {}
    for _, lang, _ in texts_with_langs:
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    
    logging.info("Detected languages:")
    for lang, count in lang_counts.items():
        logging.info(f"  - {lang}: {count} segments")
    
    # Perform batch translation
    translated_texts = batch_translate_text(texts_with_langs, target)
    
    # Map translated texts back to cells
    text_index = 0
    for cell in cells:
        if cell.get("text"):
            cell["text_vi"] = translated_texts[text_index]
            text_index += 1
    
    return cells