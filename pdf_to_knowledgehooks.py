import os
import pandas as pd
from collections import defaultdict
from hashlib import sha256
from wordfreq import word_frequency
from alive_progress import alive_bar
from com_worktwins_data_source.PDFBook import PDFBook
import spacy
import unicodedata
import json

# File paths
PDF_PATH = "com_worktwins_data/books_pdf/Bruce Eckel - Thinking in Java 4th Edition.pdf"

# Constants
MIN_BOOK_FREQUENCY = 10  # Minimum frequency in the book for inclusion
ENGLISH_TOP_PERCENTILE = 0.9  # Top 10% of English frequency
BOOK_TOP_PERCENTILE = 0.9  # Top 10% of book frequency

# Load spaCy model
nlp = spacy.load("en_core_web_sm")


def save_to_txt(data, output_path):
    """
    Save raw text data to a .txt file.
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(data)
    print(f"Saved TXT to {output_path}")


def save_to_json(data, output_path):
    """
    Save data to a JSON file.
    """
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    print(f"Saved JSON to {output_path}")




def generate_content_hash(sentence, book_freq_df, english_freq_df):
    """
    Generate a hash based on sorted words by their frequency in the book and English language.
    """
    # Tokenize and normalize
    words = [word.lower() for word in sentence.split() if word.isalnum()]

    # Merge frequency data
    frequencies = []
    for word in words:
        book_freq = book_freq_df.get(word, float('inf'))  # Higher means less frequent
        english_freq = english_freq_df.get(word, float('inf'))
        frequencies.append((word, book_freq, english_freq))

    # Sort by book frequency (primary) and English frequency (secondary)
    sorted_words = sorted(frequencies, key=lambda x: (x[1], x[2]))

    # Extract only the words for hashing
    sorted_word_list = [word for word, _, _ in sorted_words]
    joined_words = " ".join(sorted_word_list)

    # Generate hash
    return sha256(joined_words.encode()).hexdigest()[:8]


def clean_text(text):
    """
    Clean the text by normalizing Unicode characters and removing unwanted symbols.
    """
    # Normalize Unicode (e.g., fix 'modi\ufb01ed' -> 'modified')
    text = unicodedata.normalize("NFKC", text)

    # Remove numbers and punctuation
    words = text.split()
    words = [word for word in words if word.isalnum() and not word.isdigit()]  # Remove numbers
    return " ".join(words)

def extract_keywords(sentence, book_freq_df, english_freq_df):
    """
    Extract meaningful keywords focusing on nouns, verbs, adjectives, and proper nouns,
    while excluding predefined stopwords using spaCy's built-in stopword list.
    """
    # Tokenize and parse POS with spaCy
    doc = nlp(sentence)

    # Filter words based on part of speech and exclude stopwords
    filtered_words = [
        token.text.lower()
        for token in doc
        if token.is_alpha  # Keep alphabetic words only
        and not token.is_stop  # Exclude spaCy's built-in stopwords
        and token.pos_ in {"NOUN", "VERB", "PROPN", "ADJ"}  # Focus on relevant parts of speech
    ]

    # Get word frequencies
    word_data = [
        {
            "word": word,
            "book_frequency": book_freq_df.get(word, 0),
            "english_frequency": english_freq_df.get(word, float("inf")),
        }
        for word in filtered_words
    ]

    # Sort words by book frequency (desc) and English frequency (asc)
    sorted_words = sorted(
        word_data, key=lambda x: (-x["book_frequency"], x["english_frequency"])
    )

    # Deduplicate and select up to 10 keywords
    seen_words = set()
    top_keywords = []
    for item in sorted_words:
        if item["word"] not in seen_words:
            top_keywords.append(item["word"])
            seen_words.add(item["word"])
        if len(top_keywords) == 10:
            break

    return top_keywords


def generate_frequencies(book_text):
    """
    Generate word frequencies and related data from the book text.
    """
    # Split text into paragraphs and generate paragraph IDs
    paragraphs = [para.strip() for para in book_text.split("\n\n") if para.strip()]
    paragraph_ids = [sha256(para.encode()).hexdigest()[:8] for para in paragraphs]

    # Create a DataFrame for paragraphs
    paragraphs_df = pd.DataFrame({"id": paragraph_ids, "text": paragraphs})

    # Count word frequencies in the book
    word_counts = defaultdict(int)
    word_paragraph_map = defaultdict(set)

    with alive_bar(len(paragraphs), title="Processing paragraphs") as bar:
        for pid, para in zip(paragraph_ids, paragraphs):
            words = [word.lower() for word in para.split() if word.isalnum()]
            for word in words:
                word_counts[word] += 1
                word_paragraph_map[word].add(pid)
            bar()

    # Create a DataFrame for book word frequencies
    book_freq_df = pd.DataFrame(
        [(word, count, list(word_paragraph_map[word])) for word, count in word_counts.items()],
        columns=["word", "book_frequency", "paragraphs"],
    )

    # Add English language frequencies
    book_freq_df["english_frequency"] = book_freq_df["word"].apply(lambda word: word_frequency(word, "en"))

    # Identify high-frequency English and book words
    english_top_threshold = book_freq_df["english_frequency"].quantile(ENGLISH_TOP_PERCENTILE)
    book_top_threshold = book_freq_df["book_frequency"].quantile(BOOK_TOP_PERCENTILE)

    # Exclude connector words (high-frequency in both English and book)
    excluded_connectors = book_freq_df[
        (book_freq_df["english_frequency"] >= english_top_threshold) &
        (book_freq_df["book_frequency"] >= book_top_threshold)
    ]

    # Exclude low-frequency non-English words
    excluded_non_english = book_freq_df[
        (book_freq_df["english_frequency"] == 0) &  # Not in English language
        (book_freq_df["book_frequency"] < MIN_BOOK_FREQUENCY)  # Low frequency in book
    ]

    # Combine excluded words
    excluded_words_df = pd.concat([excluded_connectors, excluded_non_english]).drop_duplicates(subset=["word"])

    # Filter out excluded words from the main book frequencies
    book_freq_df = book_freq_df[~book_freq_df["word"].isin(excluded_words_df["word"])]

    # Sort book and English frequency data
    book_freq_df = book_freq_df.sort_values(by="book_frequency", ascending=False)
    english_freq_df = book_freq_df[["word", "english_frequency"]].sort_values(by="english_frequency", ascending=False)

    return paragraphs_df, book_freq_df, excluded_words_df, english_freq_df


def process_paragraphs(paragraphs, output_dir):
    """
    Split paragraphs into sentences and normalize only for the final output.
    """
    enriched_paragraphs = []
    with alive_bar(len(paragraphs), title="Processing sentences") as bar:
        for paragraph in paragraphs:
            paragraph_id = paragraph["id"]
            raw_text = paragraph["text"]  # Use raw paragraph text for splitting

            # Pass raw text to spaCy for sentence splitting
            doc = nlp(raw_text)
            sentences = []
            paragraph_keywords = set()

            for sent in doc.sents:
                raw_sentence = sent.text.strip()  # Keep sentence as-is for processing
                normalized_sentence = clean_text(raw_sentence)  # Normalize here

                # Extract keywords from normalized sentence
                keywords = extract_keywords(normalized_sentence, {}, {})  # Pass relevant freq dictionaries if available

                sentence_hash = f"{paragraph_id}_{generate_content_hash(normalized_sentence, {}, {})}"

                sentences.append({
                    "id": sentence_hash,
                    "type": "sentence",
                    "text": normalized_sentence,  # Use normalized version here
                    "keywords": keywords,
                    "weight": 0.0,
                })
                paragraph_keywords.update(keywords)

            # Sort the paragraph-level keywords
            sorted_paragraph_keywords = sorted(paragraph_keywords)

            enriched_paragraphs.append({
                "id": paragraph_id,
                "type": "paragraph",
                "text": clean_text(raw_text),  # Normalize paragraph text for final output
                "keywords": sorted_paragraph_keywords,
                "weight": 0.0,
                "sentences": sentences
            })
            bar()

    return enriched_paragraphs


def split_into_paragraphs(raw_text):
    """
    Split raw text into paragraphs based on double newline separation.
    Each paragraph retains its raw format for accurate processing later.
    """
    paragraphs = []
    for para in raw_text.split("\n\n"):
        para = para.strip()
        if para:  # Ignore empty lines
            paragraph_id = sha256(para.encode()).hexdigest()[:8]
            paragraphs.append({"id": paragraph_id, "text": para})
    return paragraphs



def main():
    # Step 1: Extract text from the book
    book = PDFBook(PDF_PATH)

    # Step 2: Create output folder
    pdf_name = os.path.splitext(os.path.basename(PDF_PATH))[0]
    output_dir = os.path.join(os.path.dirname(PDF_PATH), pdf_name)
    os.makedirs(output_dir, exist_ok=True)

    # Step 3: Save raw text
    raw_text = book.extract_raw()
    raw_text_path = os.path.join(output_dir, f"{pdf_name}.txt")
    save_to_txt(raw_text, raw_text_path)

    # Step 4: Extract and save code blocks
    print("Extracting code blocks...")
    code_blocks = book.extract_code_blocks()
    code_blocks_json_path = os.path.join(output_dir, f"{pdf_name}_code_blocks.json")
    save_to_json(code_blocks, code_blocks_json_path)

    # Save code blocks as a Python script
    code_blocks_script_path = os.path.join(output_dir, f"{pdf_name}_code_blocks.py")
    book.extract_blocks_as_python_script(code_blocks, code_blocks_script_path)

    # Step 5: Detect paragraphs from raw text
    print("Detecting paragraphs...")
    paragraphs = split_into_paragraphs(raw_text)
    paragraphs_path = os.path.join(output_dir, f"{pdf_name}_paragraphs.json")
    save_to_json(paragraphs, paragraphs_path)

    # Step 6: Split paragraphs into sentences
    print("Processing sentences...")
    enriched_paragraphs = process_paragraphs(paragraphs, output_dir)

    # Step 7: Save enriched paragraph data with normalized sentences
    enriched_paragraphs_path = os.path.join(output_dir, f"{pdf_name}_enriched_paragraphs.json")
    save_to_json(enriched_paragraphs, enriched_paragraphs_path)


if __name__ == "__main__":
    main()