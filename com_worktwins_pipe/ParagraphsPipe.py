import os
import re
from hashlib import sha256
from alive_progress import alive_bar
from com_worktwins_pipe.Pipe import Pipe  # Import the base Pipe class
import spacy  # For NLP sentence tokenization
from com_worktwins_pipe.WordFrequenciesPipe import WordFrequenciesPipe

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

class ParagraphsPipe(Pipe):
    """
    A Pipe subclass to split raw text into paragraphs, filter out source code blocks,
    and enrich paragraphs with sentences, keywords, and metadata.
    """
    def run(self, input_data):
        """
        Splits raw text into paragraphs, excludes paragraphs containing source code,
        and enriches them with metadata.

        Args:
            input_data (dict): Input JSON containing "raw_text" and "book_frequencies".

        Returns:
            dict: JSON with a list of enriched paragraphs.
        """
        raw_text = input_data

        # Split raw text into paragraphs
        paragraphs = self.split_into_paragraphs(raw_text)
        wordfreq = WordFrequenciesPipe(name=self.name,output_dir=self.output_dir).execute(input_data=raw_text)

        # Enrich paragraphs with keywords, sentences, and metadata
        enriched_paragraphs = self.process_paragraphs(paragraphs, wordfreq)

        return {"enriched_paragraphs": enriched_paragraphs}

    @staticmethod
    def split_into_paragraphs(raw_text):
        """
        Split raw text into paragraphs based on double newline separation and exclude paragraphs containing source code.

        Args:
            raw_text (str): The raw text extracted from a document.

        Returns:
            list: A list of dictionaries, each representing a paragraph with an ID and text.
        """
        paragraphs = []
        code_block_pattern = re.compile(r'((?:^(?: {4}|\t).+\n)+)', re.MULTILINE)  # Detect multi-line code blocks

        for para in raw_text.split("\n\n"):
            para = para.strip()
            if para:
                # Check if the paragraph contains code using the regex
                if code_block_pattern.search(para):
                    continue  # Skip paragraphs containing source code

                # Add the paragraph if it's not code
                paragraph_id = sha256(para.encode()).hexdigest()[:8]
                paragraphs.append({"id": paragraph_id, "text": para})

        return paragraphs

    @staticmethod
    def process_paragraphs(paragraphs, wordfreq):
        """
        Process paragraphs into sentences and generate enriched data.

        Args:
            paragraphs (list): List of dictionaries containing paragraph IDs and text.
            wordfreq (list): List of dictionaries with word frequencies, each containing "word", "book_frequency", and "english_frequency".

        Returns:
            list: Enriched paragraphs with sentences, keywords, and metadata.
        """
        # Convert wordfreq JSON array into a dictionary for fast lookups
        word_freq_dict = {item["word"]: item["book_frequency"] for item in wordfreq}

        enriched_paragraphs = []
        with alive_bar(len(paragraphs), title="Processing paragraphs") as bar:
            for para in paragraphs:
                paragraph_id = para["id"]
                paragraph_text = para["text"]

                # Tokenize paragraph into sentences
                doc = nlp(paragraph_text)
                sentences = []
                paragraph_keywords = set()

                for sent in doc.sents:
                    sentence_text = sent.text.strip()
                    words = [token.text.lower() for token in nlp(sentence_text) if token.is_alpha and not token.is_stop]
                    keywords = [word for word in words if word in word_freq_dict]

                    sentence_hash = f"{paragraph_id}_{sha256(sentence_text.encode()).hexdigest()[:8]}"
                    sentences.append({
                        "id": sentence_hash,
                        "type": "sentence",
                        "text": sentence_text,
                        "keywords": keywords,
                        "weight": 0.0,
                    })
                    paragraph_keywords.update(keywords)

                enriched_paragraphs.append({
                    "id": paragraph_id,
                    "type": "paragraph",
                    "text": paragraph_text,
                    "keywords": sorted(paragraph_keywords),
                    "weight": 0.0,
                    "sentences": sentences,
                })
                bar()

        return enriched_paragraphs
