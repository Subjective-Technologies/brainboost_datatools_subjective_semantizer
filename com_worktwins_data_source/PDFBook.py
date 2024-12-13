# PDFBook.py

import os
import json
import hashlib
from hashlib import sha256
from collections import defaultdict
import fitz  # PyMuPDF
import spacy
from alive_progress import alive_bar
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Import the updated Pipe subclasses
from com_worktwins_pipe.ParagraphsAndCodeUnifiedPipe import ParagraphsAndCodeUnifiedPipe
from com_worktwins_pipe.SemanticTreePipe import SemanticTreePipe
from com_worktwins_pipe.SemanticNormalizationPipe import SemanticNormalizationPipe
from com_worktwins_pipe.WordFrequenciesPipe import WordFrequenciesPipe

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

class PDFBook:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.name = os.path.splitext(os.path.basename(pdf_path))[0]
        self.output_dir = os.path.join(os.path.dirname(pdf_path), self.name)
        os.makedirs(self.output_dir, exist_ok=True)
        self.book_frequency = None
        self.english_frequency = None

    def load_word_frequencies(self):
        """
        Load word frequency data from the WordFrequenciesPipe.json report.
        """
        word_freq_path = os.path.join(self.output_dir, f"{self.name}-WordFrequencies.json")

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

        txt_output_path = os.path.join(self.output_dir, f"{self.name}.txt")
        with open(txt_output_path, "w", encoding="utf-8") as f:
            f.write("\n\n".join(text_content))

        return "\n\n".join(text_content)

    def evaluate(self, keywords):
        """
        Evaluate the book for topics matching the given keywords using semantic similarity.
        """
        semantic_tree_path = os.path.join(self.output_dir, f"{self.name}-SemanticTree.json")
        if not os.path.exists(semantic_tree_path):
            raise FileNotFoundError(f"Semantic tree data not found at {semantic_tree_path}. Ensure SemanticTreePipe has run.")

        with open(semantic_tree_path, "r", encoding="utf-8") as tree_file:
            semantic_tree = json.load(tree_file)["semantic_tree"]

        keyword_embeddings = self.get_embeddings(keywords)
        matches = []
        for node_id, node in semantic_tree.items():
            node_embedding = self.get_embeddings([node["text"]])[0]
            score = cosine_similarity([node_embedding], keyword_embeddings).max()
            print(f"Node: {node['text']}, Score: {score}")  # Debugging output
            if score >= 0.7:
                matches.append({
                    "id": node_id,
                    "path": node.get("path", "Unknown"),
                    "semantics": node["text"],
                    "relevance_score": score,
                })

        return self.filter_results(matches)

    def get_embeddings(self, texts):
        """
        Generate vector embeddings for a list of texts using spaCy.
        """
        return [nlp(text).vector for text in texts]

    def filter_results(self, matches, top_n=5):
        """
        Filter and return top N results based on relevance score.
        """
        return sorted(matches, key=lambda x: -x["relevance_score"])[:top_n]

    def to_knowledge_hooks(self):
        """
        Generate all knowledge hooks for the book and save the results.
        """
        raw_text = self.extract_raw()

        # Step 1: Execute WordFrequenciesPipe
        word_frequencies_pipe = WordFrequenciesPipe(
            name="WordFrequencies",
            output_dir=self.output_dir,
            pdf_name=self.name
        )
        word_frequencies = word_frequencies_pipe.execute(input_data=raw_text)

        # Step 2: Execute ParagraphsAndCodeUnifiedPipe with WordFrequenciesPipe as a dependency
        unified_extraction_pipe = ParagraphsAndCodeUnifiedPipe(
            name="ParagraphsAndCodeUnified",
            output_dir=self.output_dir,
            pdf_name=self.name,
            dependencies=[word_frequencies_pipe]
        )
        unified_report = unified_extraction_pipe.execute(input_data=raw_text)

        # Step 3: Perform semantic normalization on the unified report
        semantic_normalization_pipe = SemanticNormalizationPipe(
            name="SemanticNormalization",
            output_dir=self.output_dir,
            pdf_name=self.name,
            dependencies=[unified_extraction_pipe]
        )
        normalized_data = semantic_normalization_pipe.execute(input_data=unified_report)

        # Step 4: Generate semantic tree
        semantic_tree_input = {
            "normalized_paragraphs": normalized_data["normalized_paragraphs"],  # Updated key
            "book_frequencies": word_frequencies,
        }
        semantic_tree_pipe = SemanticTreePipe(
            name="SemanticTree",
            output_dir=self.output_dir,
            pdf_name=self.name
        )
        semantic_tree_pipe.execute(input_data=semantic_tree_input)

        # Optionally, you can save or further process the semantic tree as needed
