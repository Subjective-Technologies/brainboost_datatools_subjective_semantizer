import os
import pandas as pd
from collections import defaultdict
from hashlib import sha256
import hashlib
import json
from pygments.lexers import guess_lexer, get_lexer_by_name
from pygments.util import ClassNotFound
from wordfreq import word_frequency
from alive_progress import alive_bar
import spacy
import json
import fitz  # PyMuPDF
from com_worktwins_languages.Language import Language
from transformers import pipeline
from com_worktwins_pipe.SemanticTreePipe import SemanticTreePipe
from com_worktwins_pipe.SemanticNormalizationPipe import SemanticNormalizationPipe
from com_worktwins_pipe.SourceCodeExtractorPipe import SourceCodeExtractorPipe
from com_worktwins_pipe.WordFrequenciesPipe import WordFrequenciesPipe
from com_worktwins_pipe.ParagraphsPipe import ParagraphsPipe



# Load spaCy model
nlp = spacy.load("en_core_web_sm")

MIN_BOOK_FREQUENCY = 10  # Minimum frequency in the book for inclusion
ENGLISH_TOP_PERCENTILE = 0.9  # Top 10% of English frequency
BOOK_TOP_PERCENTILE = 0.9  # Top 10% of book frequency

class PDFBook:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.name = os.path.splitext(os.path.basename(pdf_path))[0]
        self.output_dir = os.path.join(os.path.dirname(pdf_path), self.name)
        os.makedirs(self.output_dir, exist_ok=True)
        self.book_frequency = None  # Initialize as None
        self.english_frequency = None  # Initialize as None


    def load_word_frequencies(self):
        """
        Load word frequency data from the WordFrequenciesPipe.json report.
        """
        word_freq_path = os.path.join(self.output_dir, f"{self.name}-WordFrequenciesPipe.json")

        if not os.path.exists(word_freq_path):
            raise FileNotFoundError(f"Word frequency data not found at {word_freq_path}. Ensure WordFrequenciesPipe has run.")

        with open(word_freq_path, "r", encoding="utf-8") as wf_file:
            word_frequencies = json.load(wf_file)
            self.book_frequency = {item["word"]: item["book_frequency"] for item in word_frequencies}
            self.english_frequency = {item["word"]: item["english_frequency"] for item in word_frequencies}



    def extract_raw(self):
        """
        Extract raw text from the PDF.
        """
        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(f"The file {self.pdf_path} does not exist.")

        with fitz.open(self.pdf_path) as pdf:
            text_content = []
            total_pages = pdf.page_count
            with alive_bar(total_pages, title="Extracting Raw Text") as bar:
                for page_num in range(total_pages):
                    page = pdf[page_num]
                    text = page.get_text("text")
                    text_content.append(text)
                    bar()


        # Write to the file
        with open(os.path.join(self.output_dir + "/" + self.name + ".txt"), "w", encoding="utf-8") as f:
            f.write("".join(text_content))


        return "\n\n".join(text_content)



    def evaluate(self, keywords):
        """
        Evaluate the book for topics matching the given keywords using word frequencies.
        """
        if self.book_frequency is None or self.english_frequency is None:
            self.load_word_frequencies()  # Ensure frequencies are loaded

        # Normalize and sort keywords
        normalized_keywords = [kw.lower() for kw in keywords]
        sorted_keywords = sorted(
            normalized_keywords,
            key=lambda kw: (
                -self.book_frequency.get(kw, 0),  # Descending book frequency
                self.english_frequency.get(kw, float('inf'))  # Ascending English frequency
            ),
        )

        # Further processing logic goes here...
        print(f"Sorted keywords for evaluation: {sorted_keywords}")
        # Placeholder for matching topics
        return []


    def to_knowledge_hooks(self):
        """
        Generate all knowledge hooks for the book and save the results.
        """
        raw_text = self.extract_raw()

        # Step 1: Generate word frequencies
        word_frequencies = WordFrequenciesPipe(name=self.name, output_dir=self.output_dir).execute(input_data=raw_text)

        # Step 2: Extract code snippets
        code_snippets = SourceCodeExtractorPipe(name=self.name, output_dir=self.output_dir).execute(input_data=raw_text)

        # Step 3: Process and enrich paragraphs
        paragraphs = ParagraphsPipe(name=self.name, output_dir=self.output_dir).execute(input_data=raw_text)

        # Step 4: Perform semantic normalization (include code snippets)
        input_data_for_normalization = {
            "enriched_paragraphs": paragraphs["enriched_paragraphs"],
            "code_snippets": code_snippets["code_snippets"],
        }
        normalized_paragraphs = SemanticNormalizationPipe(name=self.name, output_dir=self.output_dir).execute(
            input_data=input_data_for_normalization
        )

        # Step 5: Generate semantic tree
        input_data_for_tree = {
            "normalized_paragraphs": normalized_paragraphs["normalized_paragraphs"],
            "book_frequencies": word_frequencies,
        }
        SemanticTreePipe(name=self.name, output_dir=self.output_dir).execute(input_data=input_data_for_tree)

