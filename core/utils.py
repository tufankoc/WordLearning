import re
from collections import Counter
import requests

# NLTK imports with safe fallbacks
try:
    import nltk
    from nltk.corpus import stopwords, wordnet
    from nltk.stem import WordNetLemmatizer
    from nltk.tokenize import word_tokenize
    _NLTK_AVAILABLE = True
except Exception:
    _NLTK_AVAILABLE = False

# Ensure stopwords are downloaded
# NLTK data was downloaded in a previous step
# nltk.download('stopwords')
# nltk.download('punkt')
# nltk.download('averaged_perceptron_tagger')
# nltk.download('wordnet')

if _NLTK_AVAILABLE:
    try:
        lemmatizer = WordNetLemmatizer()
        stop_words = set(stopwords.words('english'))
    except LookupError:
        # Attempt to lazily download missing corpora at runtime in dev
        try:
            nltk.download('stopwords', quiet=True)
            nltk.download('punkt', quiet=True)
            nltk.download('averaged_perceptron_tagger', quiet=True)
            nltk.download('wordnet', quiet=True)
            lemmatizer = WordNetLemmatizer()
            stop_words = set(stopwords.words('english'))
        except Exception:
            # Final fallback to minimal behavior
            lemmatizer = None
            stop_words = set()
else:
    lemmatizer = None
    stop_words = set()

# Stop words utility functions

# Comprehensive English stop words list
ENGLISH_STOP_WORDS = {
    # Articles
    "a", "an", "the",
    
    # Pronouns
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them",
    "my", "your", "his", "her", "its", "our", "their", "myself", "yourself", "himself",
    "herself", "itself", "ourselves", "yourselves", "themselves", "this", "that", "these",
    "those", "who", "whom", "whose", "which", "what",
    
    # Prepositions
    "in", "on", "at", "by", "for", "with", "without", "to", "from", "up", "down",
    "out", "off", "over", "under", "above", "below", "between", "among", "through",
    "during", "before", "after", "since", "until", "of", "about", "into", "onto",
    "upon", "within", "across", "against", "toward", "towards", "behind", "beside",
    "beyond", "near", "around",
    
    # Conjunctions
    "and", "or", "but", "so", "yet", "nor", "for", "if", "when", "where", "why",
    "how", "while", "although", "though", "because", "since", "unless", "until",
    "whether", "either", "neither", "both", "not", "only",
    
    # Auxiliary verbs and common verbs
    "am", "is", "are", "was", "were", "be", "being", "been", "have", "has", "had",
    "do", "does", "did", "will", "would", "shall", "should", "may", "might", "can",
    "could", "must", "ought",
    
    # Common adverbs
    "not", "no", "yes", "here", "there", "where", "when", "how", "why", "then",
    "now", "today", "yesterday", "tomorrow", "always", "never", "sometimes",
    "often", "usually", "very", "quite", "rather", "too", "also", "just", "only",
    "even", "still", "already", "yet", "again", "more", "most", "much", "many",
    "few", "little", "less", "least", "all", "some", "any", "each", "every",
    "another", "other", "such", "same", "different",
    
    # Common question words and misc
    "as", "than", "like", "so", "well", "than", "such", "way", "too", "first",
    "last", "next", "new", "old", "good", "bad", "big", "small", "long", "short",
    "high", "low", "right", "left", "sure", "ok", "okay", "hello", "hi", "bye",
    "please", "thank", "thanks", "welcome",
    
    # Numbers (written out)
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
    "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
    "eighty", "ninety", "hundred", "thousand", "million", "billion",
    
    # Common contractions (expanded)
    "ll", "ve", "re", "d", "t", "s", "m",  # 'll, 've, 're, 'd, 't, 's, 'm
}

def is_stop_word(word):
    """
    Check if a word is a stop word.
    
    Args:
        word (str): Word to check
        
    Returns:
        bool: True if word is a stop word
    """
    return word.lower().strip() in ENGLISH_STOP_WORDS

def filter_stop_words(word_list):
    """
    Filter out stop words from a list of words.
    
    Args:
        word_list (list): List of words to filter
        
    Returns:
        list: Filtered list without stop words
    """
    return [word for word in word_list if not is_stop_word(word)]

def calculate_content_score(word, frequency, filter_stop_words_enabled=True):
    """
    Calculate content score for a word, considering stop word filtering.
    
    Args:
        word (str): The word
        frequency (int): Raw frequency count
        filter_stop_words_enabled (bool): Whether to apply stop word penalty
        
    Returns:
        float: Adjusted score (frequency * penalty factor)
    """
    if filter_stop_words_enabled and is_stop_word(word):
        # Heavily penalize stop words but don't eliminate them completely
        return frequency * 0.1
    
    return float(frequency)

def get_stop_words_stats(word_counts):
    """
    Get statistics about stop words vs content words.
    
    Args:
        word_counts (dict): Dictionary of word -> frequency
        
    Returns:
        dict: Statistics about stop words and content words
    """
    total_words = sum(word_counts.values())
    total_unique = len(word_counts)
    
    stop_word_count = 0
    stop_word_frequency = 0
    content_word_count = 0
    content_word_frequency = 0
    
    for word, freq in word_counts.items():
        if is_stop_word(word):
            stop_word_count += 1
            stop_word_frequency += freq
        else:
            content_word_count += 1
            content_word_frequency += freq
    
    return {
        'total_words': total_words,
        'total_unique': total_unique,
        'stop_words': {
            'unique_count': stop_word_count,
            'total_frequency': stop_word_frequency,
            'percentage_of_unique': (stop_word_count / total_unique * 100) if total_unique > 0 else 0,
            'percentage_of_total': (stop_word_frequency / total_words * 100) if total_words > 0 else 0,
        },
        'content_words': {
            'unique_count': content_word_count,
            'total_frequency': content_word_frequency,
            'percentage_of_unique': (content_word_count / total_unique * 100) if total_unique > 0 else 0,
            'percentage_of_total': (content_word_frequency / total_words * 100) if total_words > 0 else 0,
        }
    }

def get_content_preview(content, max_length=200):
    """
    Generate a preview of content with proper truncation.
    
    Args:
        content (str): Full content text
        max_length (int): Maximum length for preview
        
    Returns:
        str: Truncated preview with ellipsis if needed
    """
    if not content:
        return "No content available"
    
    # Clean up the content
    clean_content = content.strip()
    
    # If content is short enough, return as is
    if len(clean_content) <= max_length:
        return clean_content
    
    # Truncate and add ellipsis
    truncated = clean_content[:max_length].rsplit(' ', 1)[0]  # Don't cut words in half
    return truncated + "..."

def get_wordnet_pos(word):
    """Map POS tag to first character lemmatize() accepts. Falls back to NOUN if NLTK unavailable."""
    if not _NLTK_AVAILABLE:
        # Default to noun if tagging is unavailable
        return None
    try:
        tag = nltk.pos_tag([word])[0][1][0].upper()
        tag_dict = {
            "J": wordnet.ADJ,
            "N": wordnet.NOUN,
            "V": wordnet.VERB,
            "R": wordnet.ADV,
        }
        return tag_dict.get(tag, wordnet.NOUN)
    except Exception:
        return None

def extract_words_from_text(text: str) -> Counter:
    """
    Normalizes a text by tokenizing, lemmatizing, and removing stopwords,
    and returns a Counter with word frequencies.
    """
    # Remove URLs
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    # Remove HTML tags
    text = re.sub(r'<.*?>', '', text)
    # Remove non-alphanumeric characters but keep apostrophes
    text = re.sub(r"[^a-zA-Z0-9']+", " ", text)
    
    # Tokenization fallback: if NLTK not available, split on whitespace
    if _NLTK_AVAILABLE:
        try:
            tokens = word_tokenize(text.lower())
        except LookupError:
            try:
                nltk.download('punkt', quiet=True)
                tokens = word_tokenize(text.lower())
            except Exception:
                tokens = re.findall(r"[a-zA-Z']+", text.lower())
    else:
        tokens = re.findall(r"[a-zA-Z']+", text.lower())

    lemmatized_words: list[str] = []
    for word in tokens:
        if word.isalpha() and (not stop_words or word not in stop_words) and len(word) > 2:
            if _NLTK_AVAILABLE and lemmatizer is not None:
                pos = get_wordnet_pos(word) or wordnet.NOUN if _NLTK_AVAILABLE else None
                try:
                    lemma = lemmatizer.lemmatize(word, pos) if pos else lemmatizer.lemmatize(word)
                except Exception:
                    lemma = word
            else:
                lemma = word
            lemmatized_words.append(lemma)

    return Counter(lemmatized_words)

def fetch_word_definition(word_text: str) -> str | None:
    """
    Fetches the first definition of a word from the Free Dictionary API.
    """
    try:
        response = requests.get(
            f"https://api.dictionaryapi.dev/api/v2/entries/en/{word_text}",
            timeout=5,
        )
        if response.status_code == 200:
            data = response.json()
            # Extract the first definition from the complex structure
            definition = data[0]['meanings'][0]['definitions'][0]['definition']
            return definition
    except (requests.RequestException, IndexError, KeyError):
        # If the request fails, or the JSON structure is not as expected, or the word is not found
        return None
    return None 


def enrich_word_with_dictionaryapi(word_text: str) -> dict:
    """
    Fetch detailed word data (definition, phonetic, audio, examples, synonyms/antonyms, POS)
    from Free Dictionary API, with safe fallbacks.

    Returns a dict with optional keys: definition, phonetic, audio_url,
    example_sentence, synonyms, antonyms, part_of_speech.
    """
    result: dict = {}
    try:
        resp = requests.get(
            f"https://api.dictionaryapi.dev/api/v2/entries/en/{word_text}", timeout=5
        )
        if resp.status_code != 200:
            return result
        data = resp.json()
        if not isinstance(data, list) or not data:
            return result
        entry = data[0]
        # Phonetic
        phonetic = entry.get('phonetic') or ''
        if not phonetic and entry.get('phonetics'):
            for ph in entry['phonetics']:
                if isinstance(ph, dict) and ph.get('text'):
                    phonetic = ph['text']
                    break
        if phonetic:
            result['phonetic'] = phonetic
        # Audio
        audio_url = None
        for ph in entry.get('phonetics', []) or []:
            if isinstance(ph, dict) and ph.get('audio'):
                audio_url = ph['audio']
                if audio_url:
                    break
        if audio_url:
            result['audio_url'] = audio_url
        # Meanings
        meanings = entry.get('meanings') or []
        synonyms: list[str] = []
        antonyms: list[str] = []
        example_sentence = None
        part_of_speech = None
        definition = None
        for m in meanings:
            if not isinstance(m, dict):
                continue
            if not part_of_speech and m.get('partOfSpeech'):
                part_of_speech = m['partOfSpeech']
            defs = m.get('definitions') or []
            if defs and isinstance(defs[0], dict):
                if not definition and defs[0].get('definition'):
                    definition = defs[0]['definition']
                if not example_sentence and defs[0].get('example'):
                    example_sentence = defs[0]['example']
            # collect synonyms/antonyms
            if m.get('synonyms') and isinstance(m['synonyms'], list):
                synonyms.extend([s for s in m['synonyms'] if isinstance(s, str)])
            if m.get('antonyms') and isinstance(m['antonyms'], list):
                antonyms.extend([a for a in m['antonyms'] if isinstance(a, str)])
        if definition:
            result['definition'] = definition
        if example_sentence:
            result['example_sentence'] = example_sentence
        if synonyms:
            result['synonyms'] = list(dict.fromkeys(synonyms))[:10]
        if antonyms:
            result['antonyms'] = list(dict.fromkeys(antonyms))[:10]
        if part_of_speech:
            result['part_of_speech'] = part_of_speech
        return result
    except requests.RequestException:
        return result