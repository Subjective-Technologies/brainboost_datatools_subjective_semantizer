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
ENGLISH_FREQUENCIES_PATH = "report_english_frequencies.json"
BOOK_FREQUENCIES_PATH = "report_book_frequencies.json"
BOOK_PARAGRAPHS_PATH = "report_book_paragraphs.json"
EXCLUDED_WORDS_PATH = "report_excluded_words.json"

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


def create_output_folder(pdf_path):
    """
    Create an output folder with the same name as the PDF file.
    """
    folder_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_dir = os.path.join(os.path.dirname(pdf_path), folder_name)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def prepend_pdf_name(output_dir, pdf_path, suffix):
    """
    Generate file path with the PDF file name prepended in the output directory.
    """
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    return os.path.join(output_dir, f"{base_name}_{suffix}")




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
    Extract the most meaningful keywords for a sentence.
    """
    # Tokenize and normalize
    words = [word.lower() for word in sentence.split() if word.isalnum() and len(word) >= 3]

    # Get frequencies
    word_data = [
        {
            "word": word,
            "book_frequency": book_freq_df.get(word, 0),
            "english_frequency": english_freq_df.get(word, float("inf")),
        }
        for word in words
    ]

    # Sort by book frequency (desc) and English frequency (asc)
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


def process_paragraphs(paragraphs_df, book_freq_df, english_freq_df):
    """
    Process paragraphs and split them into sentences, generating content-based hashes and paragraph-level keywords.
    """
    book_freq_dict = book_freq_df.set_index("word")["book_frequency"].to_dict()
    english_freq_dict = english_freq_df.set_index("word")["english_frequency"].to_dict()

    enriched_paragraphs = []
    with alive_bar(len(paragraphs_df), title="Processing sentences") as bar:
        for _, paragraph in paragraphs_df.iterrows():
            paragraph_id = paragraph["id"]
            paragraph_text = clean_text(paragraph["text"])

            # Use spaCy to tokenize into sentences
            doc = nlp(paragraph_text)
            sentences = []
            paragraph_keywords = set()
            
            for sent in doc.sents:
                sentence_text = clean_text(sent.text)
                keywords = extract_keywords(sentence_text, book_freq_dict, english_freq_dict)
                sentence_hash = f"{paragraph_id}_{generate_content_hash(sentence_text, book_freq_dict, english_freq_dict)}"

                sentences.append({
                    "id": sentence_hash,
                    "type": "sentence",
                    "text": sentence_text,
                    "keywords": keywords,
                    "weight": 0.0
                })
                # Accumulate keywords from each sentence
                paragraph_keywords.update(keywords)

            # Sort the paragraph-level keywords
            sorted_paragraph_keywords = sorted(
                paragraph_keywords,
                key=lambda word: (-book_freq_dict.get(word, 0), english_freq_dict.get(word, float('inf')))
            )

            enriched_paragraphs.append({
                "id": paragraph_id,
                "type": "paragraph",
                "text": paragraph_text,
                "keywords": sorted_paragraph_keywords,
                "weight": 0.0,
                "sentences": sentences
            })
            bar()

    return enriched_paragraphs


def main():
    # Step 1: Create output folder
    output_dir = create_output_folder(PDF_PATH)

    # Step 2: Extract text from the book
    book = PDFBook(PDF_PATH)

    # Step 3: Save raw text
    raw_text = book.extract_raw()
    raw_text_path = prepend_pdf_name(output_dir, PDF_PATH, "raw_text.txt")
    save_to_txt(raw_text, raw_text_path)

    # Step 4: Extract and save code blocks
    print("Extracting code blocks...")
    code_blocks = book.extract_code_blocks()
    code_blocks_json_path = prepend_pdf_name(output_dir, PDF_PATH, "code_blocks.json")
    save_to_json(code_blocks, code_blocks_json_path)

    code_blocks_script_path = prepend_pdf_name(output_dir, PDF_PATH, "code_blocks.py")
    book.save_code_blocks_as_python_script(code_blocks, code_blocks_script_path)

    # Step 5: Normalize text and generate frequencies
    normalized_text = book.extract_normalized()
    print("Generating frequencies and paragraphs...")
    paragraphs_df, book_freq_df, excluded_words_df, english_freq_df = generate_frequencies(normalized_text)

    # Step 6: Save initial results to JSON files
    save_to_json(paragraphs_df.to_dict(orient="records"), prepend_pdf_name(output_dir, PDF_PATH, "paragraphs.json"))
    save_to_json(book_freq_df[["word", "book_frequency", "paragraphs"]].to_dict(orient="records"),
                 prepend_pdf_name(output_dir, PDF_PATH, "book_frequencies.json"))
    save_to_json(english_freq_df.to_dict(orient="records"),
                 prepend_pdf_name(output_dir, PDF_PATH, "english_frequencies.json"))
    save_to_json(excluded_words_df[["word", "paragraphs"]].to_dict(orient="records"),
                 prepend_pdf_name(output_dir, PDF_PATH, "excluded_words.json"))

    # Step 7: Process paragraphs into sentences
    print("Processing sentences...")
    enriched_paragraphs = process_paragraphs(paragraphs_df, book_freq_df, english_freq_df)

    # Step 8: Save enriched paragraph data with sentences
    enriched_paragraphs_path = prepend_pdf_name(output_dir, PDF_PATH, "paragraphs_with_sentences.json")
    save_to_json(enriched_paragraphs, enriched_paragraphs_path)

    print(f"All outputs saved in {output_dir}")

