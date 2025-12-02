def analyze_text(text: str) -> str:
    """
    Analyze text and return statistics.

    Args:
        text: The text to analyze

    Returns:
        Text analysis statistics as a formatted string

    Examples:
        analyze_text("Hello world!") -> "Characters: 12, Words: 2, Sentences: 1, Average word length: 5.0"
    """
    if not text or not text.strip():
        return "Error: Please provide some text to analyze."

    # Clean the text
    cleaned_text = text.strip()

    # Count characters (including spaces)
    char_count = len(cleaned_text)

    # Count characters without spaces
    char_no_spaces = len(cleaned_text.replace(" ", ""))

    # Count words
    words = cleaned_text.split()
    word_count = len(words)

    # Count sentences (basic approximation)
    sentence_count = len([s for s in cleaned_text.split('.') if s.strip()]) + \
                     len([s for s in cleaned_text.split('!') if s.strip()]) + \
                     len([s for s in cleaned_text.split('?') if s.strip()])

    # Remove duplicates for sentence counting
    sentences = cleaned_text.replace('!', '.').replace('?', '.').split('.')
    sentence_count = len([s for s in sentences if s.strip()])

    # Average word length
    avg_word_length = sum(len(word) for word in words) / word_count if word_count > 0 else 0

    # Most common words (excluding common stop words)
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}
    filtered_words = [word.lower() for word in words if word.lower() not in stop_words]
    word_freq = {}
    for word in filtered_words:
        word_freq[word] = word_freq.get(word, 0) + 1

    most_common = max(word_freq.items(), key=lambda x: x[1]) if word_freq else ("N/A", 0)

    result = f"""Text Analysis:
• Characters (with spaces): {char_count}
• Characters (no spaces): {char_no_spaces}
• Words: {word_count}
• Sentences: {sentence_count}
• Average word length: {avg_word_length:.1f}
• Most common word: '{most_common[0]}' (appears {most_common[1]} times)"""

    return result