# SemanticNormalizationPipe.py

import hashlib
import json
import os
import torch
from transformers import pipeline
from alive_progress import alive_bar
from com_worktwins_pipe.Pipe import Pipe  # Import the updated base Pipe class

class SemanticNormalizationPipe(Pipe):
    def __init__(self, name, output_dir, pdf_name, dependencies=None):
        """
        Initializes the SemanticNormalizationPipe.

        Args:
            name (str): The name of the pipe (e.g., 'SemanticNormalization').
            output_dir (str): The directory where output files will be saved.
            pdf_name (str): The base name of the PDF being processed.
            dependencies (list, optional): List of dependent Pipe instances.
        """
        super().__init__(name, output_dir, pdf_name, dependencies)
        device = 0 if torch.cuda.is_available() else -1
        self.bart_model = pipeline("summarization", model="facebook/bart-large-cnn", device=device)

    def run(self, input_data):
        """
        Normalizes the semantics of entries in the unified report.

        Args:
            input_data (dict): Input JSON containing "unified_report".

        Returns:
            dict: JSON containing normalized data with a "normalized_paragraphs" field.
        """
        unified_report = input_data.get("unified_report", [])
        if not unified_report:
            raise ValueError("Input data must contain 'unified_report'.")

        normalized_paragraphs = []
        with alive_bar(len(unified_report), title="Normalizing Semantics") as bar:
            for entry in unified_report:
                if entry["type"] == "paragraph":
                    normalized_entry = self.normalize_paragraph(entry)
                elif entry["type"] == "source_code":
                    normalized_entry = self.handle_source_code(entry)
                else:
                    # For unknown types, pass them through without changes
                    normalized_entry = entry
                normalized_paragraphs.append(normalized_entry)
                bar()

        return {"normalized_paragraphs": normalized_paragraphs}

    def normalize_paragraph(self, paragraph):
        """
        Normalize a paragraph entry by summarizing its text.

        Args:
            paragraph (dict): Paragraph data.

        Returns:
            dict: Normalized paragraph with a "semantics" field.
        """
        try:
            semantics = self.bart_model(
                paragraph["text"],
                max_length=130,
                min_length=30,
                do_sample=False
            )[0]["summary_text"]
        except Exception as e:
            print(f"Error normalizing paragraph {paragraph['id']}: {e}")
            semantics = paragraph["text"]  # Fallback to original text

        return {
            "id": paragraph["id"],
            "type": paragraph["type"],
            "text": paragraph["text"],
            "semantics": semantics,
            "keywords": paragraph["keywords"],
            "weight": paragraph["weight"],
            "sentences": paragraph.get("sentences", []),
        }

    def handle_source_code(self, code_snippet):
        """
        Handle a source code entry. For now, we can pass it through or add additional processing if needed.

        Args:
            code_snippet (dict): Source code data.

        Returns:
            dict: Source code entry, potentially with modifications.
        """
        # Example: You might want to add code normalization or analysis here
        # For now, we'll pass it through without changes
        return code_snippet
