def normalize_spaced_text(text):
    """
    Normalize text with excessive spacing between characters,
    commonly found in headers like "F I N A N C I A L  S T A T E M E N T S" or ""
    """
    # Check if text has consistent spacing pattern (every character followed by space)
    if len(text) > 3 and all(text[i] == ' ' for i in range(1, len(text), 2)):
        # Join characters by removing spaces
        return ''.join(text[i] for i in range(0, len(text), 2))
    
    # Check if text has spaces between all characters
    if len(text) > 3 and ' ' in text:
        # Count spaces vs non-spaces
        spaces = text.count(' ')
        non_spaces = len(text) - spaces
        
        # If the ratio of spaces to characters is high (e.g., spaces >= characters)
        if spaces >= non_spaces - 1:
            text_split = text.split(' ')
            text_split = [' ' if char == '' else char for char in text_split]
            return ''.join(text_split)
    
    # Return original if no patterns match
    return text


def clean_text(text):
    """Clean text by removing/replacing non-printable characters"""
    if not isinstance(text, str):
        return text
        
    # Replace common problematic Unicode characters
    replacements = {
        '\u0000': '',  # NULL
        '\u0001': '',  # START OF HEADING
        '\u0002': '',  # START OF TEXT
        '\u0003': '',  # END OF TEXT
        '\u0004': '',  # END OF TRANSMISSION
        '\u0005': '',  # ENQUIRY
        '\u0006': '',  # ACKNOWLEDGE
        '\u0007': '',  # BELL
        '\u0014': '',  # DEVICE CONTROL FOUR
        '\u0015': '',  # NEGATIVE ACKNOWLEDGE
        '\ufffd': '',  # REPLACEMENT CHARACTER (�)
        '\u200b': '',  # ZERO WIDTH SPACE
        '\u200e': '',  # LEFT-TO-RIGHT MARK
        '\u200f': '',  # RIGHT-TO-LEFT MARK
        '\ufeff': '',  # ZERO WIDTH NO-BREAK SPACE
    }
    
    # Apply replacements
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    
    # Filter out any remaining control characters
    return ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')