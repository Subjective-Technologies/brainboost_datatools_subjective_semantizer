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

# Constants
BOOKS_DIR = "com_worktwins_data/books_pdf"  # Directory containing the PDFs
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
    words = [word.lower() for word in sentence.split() if word.isalnum()]
    frequencies = [(word, book_freq_df.get(word, float('inf')), english_freq_df.get(word, float('inf')))
                   for word in words]
    sorted_words = sorted(frequencies, key=lambda x: (x[1], x[2]))
    sorted_word_list = [word for word, _, _ in sorted_words]
    joined_words = " ".join(sorted_word_list)
    return sha256(joined_words.encode()).hexdigest()[:8]


def clean_text(text):
    """
    Clean the text by normalizing Unicode characters and removing unwanted symbols.
    """
    text = unicodedata.normalize("NFKC", text)
    words = text.split()
    words = [word for word in words if word.isalnum() and not word.isdigit()]
    return " ".join(words)


def extract_keywords(sentence, book_freq_df, english_freq_df):
    """
    Extract the most meaningful keywords for a sentence.
    """
    words = [word.lower() for word in sentence.split() if word.isalnum() and len(word) >= 3]
    word_data = [
        {
            "word": word,
            "book_frequency": book_freq_df.get(word, 0),
            "english_frequency": english_freq_df.get(word, float("inf")),
        }
        for word in words
    ]
    sorted_words = sorted(word_data, key=lambda x: (-x["book_frequency"], x["english_frequency"]))
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
    paragraphs = [para.strip() for para in book_text.split("\n\n") if para.strip()]
    paragraph_ids = [sha256(para.encode()).hexdigest()[:8] for para in paragraphs]
    paragraphs_df = pd.DataFrame({"id": paragraph_ids, "text": paragraphs})

    word_counts = defaultdict(int)
    word_paragraph_map = defaultdict(set)

    with alive_bar(len(paragraphs), title="Processing paragraphs") as bar:
        for pid, para in zip(paragraph_ids, paragraphs):
            words = [word.lower() for word in para.split() if word.isalnum()]
            for word in words:
                word_counts[word] += 1
                word_paragraph_map[word].add(pid)
            bar()

    book_freq_df = pd.DataFrame(
        [(word, count, list(word_paragraph_map[word])) for word, count in word_counts.items()],
        columns=["word", "book_frequency", "paragraphs"],
    )
    book_freq_df["english_frequency"] = book_freq_df["word"].apply(lambda word: word_frequency(word, "en"))

    english_top_threshold = book_freq_df["english_frequency"].quantile(ENGLISH_TOP_PERCENTILE)
    book_top_threshold = book_freq_df["book_frequency"].quantile(BOOK_TOP_PERCENTILE)

    excluded_connectors = book_freq_df[
        (book_freq_df["english_frequency"] >= english_top_threshold) &
        (book_freq_df["book_frequency"] >= book_top_threshold)
    ]
    excluded_non_english = book_freq_df[
        (book_freq_df["english_frequency"] == 0) & (book_freq_df["book_frequency"] < MIN_BOOK_FREQUENCY)
    ]
    excluded_words_df = pd.concat([excluded_connectors, excluded_non_english]).drop_duplicates(subset=["word"])
    book_freq_df = book_freq_df[~book_freq_df["word"].isin(excluded_words_df["word"])]
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
                paragraph_keywords.update(keywords)

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


def process_all_pdfs(directory):
    """
    Process all PDFs in a given directory.
    """
    for filename in os.listdir(directory):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(directory, filename)
            pdf_name = os.path.splitext(filename)[0]
            output_dir = os.path.join(directory, pdf_name)
            os.makedirs(output_dir, exist_ok=True)

            book = PDFBook(pdf_path)

            # Save raw text
            raw_text = book.extract_raw()
            save_to_txt(raw_text, os.path.join(output_dir, f"{pdf_name}.txt"))

            # Extract and save code blocks
            print(f"Extracting code blocks for {pdf_name}...")
            code_blocks = book.extract_code_blocks()
            save_to_json(code_blocks, os.path.join(output_dir, f"{pdf_name}_code_blocks.json"))
            book.save_code_blocks_as_python_script(code_blocks, os.path.join(output_dir, f"{pdf_name}_code_blocks.py"))

            # Normalize text and generate frequencies
            normalized_text = book.extract_normalized()
            print(f"Generating frequencies and paragraphs for {pdf_name}...")
            paragraphs_df, book_freq_df, excluded_words_df, english_freq_df = generate_frequencies(normalized_text)

            # Save results to JSON
            save_to_json(paragraphs_df.to_dict(orient="records"), os.path.join(output_dir, f"{pdf_name}_paragraphs.json"))
            save_to_json(book_freq_df[["word", "book_frequency", "paragraphs"]].to_dict(orient="records"),
                         os.path.join(output_dir, f"{pdf_name}_frequencies.json"))
            save_to_json(english_freq_df.to_dict(orient="records"),
                         os.path.join(output_dir, f"{pdf_name}_english_frequencies.json"))
            save_to_json(excluded_words_df[["word", "paragraphs"]].to_dict(orient="records"),
                         os.path.join(output_dir, f"{pdf_name}_excluded_words.json"))

            # Process paragraphs into sentences
            print(f"Processing sentences for {pdf_name}...")
            enriched_paragraphs = process_paragraphs(paragraphs_df, book_freq_df, english_freq_df)
            save_to_json(enriched_paragraphs, os.path.join(output_dir, f"{pdf_name}_enriched_paragraphs.json"))


if __name__ == "__main__":
    process_all_pdfs(BOOKS_DIR)
