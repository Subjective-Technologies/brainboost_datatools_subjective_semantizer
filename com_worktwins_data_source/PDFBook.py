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
from com_worktwins_pipe.WordFrequencesPipe import WordFrequencesPipe
from com_worktwins_pipe.ParagraphsPipe import ParagraphsPipe



# Load spaCy model
nlp = spacy.load("en_core_web_sm")

MIN_BOOK_FREQUENCY = 10  # Minimum frequency in the book for inclusion
ENGLISH_TOP_PERCENTILE = 0.9  # Top 10% of English frequency
BOOK_TOP_PERCENTILE = 0.9  # Top 10% of book frequency

class PDFBook:
    def __init__(self, pdf_path):
        """
        Initialize the PDFBook class with the path to a PDF file.
        """
        self.pdf_path = pdf_path
        self.name = os.path.splitext(os.path.basename(pdf_path))[0]
        self.output_dir = os.path.join(os.path.dirname(pdf_path), self.name)
        os.makedirs(self.output_dir, exist_ok=True)

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

        return "\n\n".join(text_content)



    def evaluate(self, keywords):
        """
        Evaluate the book for topics matching the given keywords using the semantic tree.
        """
        # Normalize and sort keywords
        normalized_keywords = [kw.lower() for kw in keywords]
        sorted_keywords = sorted(normalized_keywords, key=lambda kw: (
            -self.book_freq_dict.get(kw, 0),  # Descending book frequency
            self.english_freq_dict.get(kw, float('inf'))  # Ascending English frequency
        ))

        # Generate hash for the keyword combination
        keyword_hash = hashlib.md5("".join(sorted_keywords).encode()).hexdigest()

        # Search for the hash in the semantic tree
        semantic_tree_path = os.path.join(self.output_dir, f"{self.name}_semantic_tree.json")
        if not os.path.exists(semantic_tree_path):
            raise FileNotFoundError("Semantic tree file not found. Ensure to_knowledge_hooks has been run.")

        with open(semantic_tree_path, "r", encoding="utf-8") as f:
            semantic_tree = json.load(f)

        # Find the matching topic
        matched_topic = semantic_tree.get(keyword_hash)

        # Debug information
        print("[DEBUG] No match found for keywords:", keywords)
        print("[DEBUG] Normalized Keywords:", normalized_keywords)
        print("[DEBUG] Sorted Keywords:", sorted_keywords)
        print("[DEBUG] Generated Hash:", keyword_hash)

        # If no match is found, return an empty list
        if not matched_topic:
            return []

        # Format the result
        return [{
            "id": matched_topic["id"],
            "path": matched_topic["path"],
            "semantics": matched_topic["semantics"],
            "matched_keywords": keywords,
            "relevance_score": 1.0  # Placeholder for more complex relevance scoring
        }]



    def to_knowledge_hooks(self):
        """
        Generate all knowledge hooks for the book and save the results.
        """
        raw_text = self.extract_raw()

        word_frequencies = WordFrequencesPipe(name=self.name,output_dir=self.output_dir).execute(input_data=raw_text)

        paragraphs = ParagraphsPipe(name=self.name,output_dir=self.output_dir,dependencies=[word_frequencies]).execute(input_data=raw_text)
        code_blocks = SourceCodeExtractorPipe(name=self.name,output_dir=self.output_dir).execute(input_data=raw_text)
        normalized_paragraphs = SemanticNormalizationPipe(name=self.name,output_dir=self.output_dir).execute(input_data=paragraphs)
        semamtic_tree = SemanticTreePipe(name=self.name,output_dir=self.output_dir).execute(input_data=normalized_paragraphs)








