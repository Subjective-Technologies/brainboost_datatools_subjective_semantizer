import hashlib
import json
import os
import torch
from transformers import pipeline
from alive_progress import alive_bar
from com_worktwins_pipe.Pipe import Pipe  # Import the base Pipe class

class SemanticNormalizationPipe(Pipe):
    """
    A Pipe subclass to normalize the semantics of enriched paragraphs using BART.
    """
    def run(self, input_data):
        """
        Normalizes the semantics of enriched paragraphs.

        Args:
            input_data (dict): Input JSON containing "enriched_paragraphs".

        Returns:
            dict: JSON containing normalized paragraphs with a "semantics" field.
        """
        enriched_paragraphs = input_data.get("enriched_paragraphs", [])

        if not enriched_paragraphs:
            raise ValueError("Input data must contain 'enriched_paragraphs'.")

        # Perform semantic normalization
        normalized_paragraphs = self.extract_semantics(enriched_paragraphs)
        return {"normalized_paragraphs": normalized_paragraphs}

    def extract_semantics(self, enriched_paragraphs):
        """
        Normalize the knowledge of the book semantically using BART, outputting to a 'semantics' field.

        Args:
            enriched_paragraphs (list): List of enriched paragraphs to normalize.

        Returns:
            list: Normalized paragraphs with a 'semantics' field added.
        """
        # Use GPU if available
        device = 0 if torch.cuda.is_available() else -1
        bart_model = pipeline("summarization", model="facebook/bart-large-cnn", device=device)

        normalized_paragraphs = []
        with alive_bar(len(enriched_paragraphs), title="Normalizing Semantics") as bar:
            for para in enriched_paragraphs:
                try:
                    # Normalize text using BART
                    semantics = bart_model(para["text"], max_length=130, min_length=30, do_sample=False)[0]["summary_text"]

                    # Include semantics field in the paragraph data
                    normalized_paragraphs.append({
                        "id": para["id"],
                        "type": para["type"],
                        "text": para["text"],  # Original text
                        "semantics": semantics,  # Added field
                        "keywords": para["keywords"],
                        "weight": para["weight"],
                        "sentences": para["sentences"],
                    })
                except Exception as e:
                    print(f"Error normalizing paragraph {para['id']}: {e}")
                finally:
                    bar()

        return normalized_paragraphs


    
    def generate_semantic_unit_id(self, keywords):
        """
        Generate a semantic unit ID based on keywords.
        Keywords are sorted by book frequency (descending) and English frequency (ascending).
        """
        # Retrieve book and English frequencies
        book_freq_path = os.path.join(self.output_dir, f"{self.name}_book_frequencies.json")
        with open(book_freq_path, "r", encoding="utf-8") as f:
            book_frequencies = {item["word"]: item["book_frequency"] for item in json.load(f)}

        english_freq_path = os.path.join(self.output_dir, f"{self.name}_english_frequencies.json")
        with open(english_freq_path, "r", encoding="utf-8") as f:
            english_frequencies = {item["word"]: item["english_frequency"] for item in json.load(f)}

        # Sort keywords by book frequency (desc) and English frequency (asc)
        sorted_keywords = sorted(
            keywords,
            key=lambda x: (
                -book_frequencies.get(x, 0),  # Descending book frequency
                english_frequencies.get(x, float("inf"))  # Ascending English frequency
            ),
        )

        # Generate a hash of the sorted keywords
        keyword_string = "|".join(sorted_keywords)
        return hashlib.sha256(keyword_string.encode()).hexdigest()[:16]  # Shorten hash for readability