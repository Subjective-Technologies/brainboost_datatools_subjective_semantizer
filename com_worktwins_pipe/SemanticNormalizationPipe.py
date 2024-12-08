import hashlib
import json
import os
import torch
from transformers import pipeline
from alive_progress import alive_bar
from com_worktwins_pipe.Pipe import Pipe  # Import the base Pipe class
from transformers import pipeline
import torch

class SemanticNormalizationPipe(Pipe):



    def __init__(self, name, output_dir):
        super().__init__(name, output_dir)
        device = 0 if torch.cuda.is_available() else -1
        self.bart_model = pipeline("summarization", model="facebook/bart-large-cnn", device=device)
        
    def extract_semantics(self, enriched_paragraphs):
        normalized_paragraphs = []
        with alive_bar(len(enriched_paragraphs), title="Normalizing Semantics") as bar:
            for para in enriched_paragraphs:
                try:
                    semantics = self.bart_model(para["text"], max_length=130, min_length=30, do_sample=False)[0]["summary_text"]
                    normalized_paragraphs.append({
                        "id": para["id"],
                        "type": para["type"],
                        "text": para["text"],
                        "semantics": semantics,
                        "keywords": para["keywords"],
                        "weight": para["weight"],
                        "sentences": para["sentences"],
                    })
                except Exception as e:
                    print(f"Error normalizing paragraph {para['id']}: {e}")
                finally:
                    bar()
        return normalized_paragraphs

    def associate_code_with_paragraphs(self,raw_text, code_snippets):
        """
        Associates source code snippets with the paragraphs that introduce them.

        Args:
            raw_text (str): The original raw text of the document.
            code_snippets (list): Extracted code snippets.

        Returns:
            dict: Mapping of paragraph IDs to associated source codes.
        """
        paragraphs = self.split_into_paragraphs(raw_text)
        associations = {para["id"]: [] for para in paragraphs}

        last_paragraph_id = None
        for line in raw_text.split("\n"):
            line = line.strip()
            if not line:
                continue
            
            # Check if the line is a paragraph
            if not line.startswith(" "):  # Paragraphs don't have leading spaces
                paragraph_id = hashlib.sha256(line.encode()).hexdigest()[:8]
                last_paragraph_id = paragraph_id
            
            # Check if the line is a code snippet
            if line.startswith("    ") or line.startswith("\t"):  # Code snippets are indented
                code_snippet_id = hashlib.sha256(line.encode()).hexdigest()[:8]
                snippet = next((code for code in code_snippets if code["id"] == code_snippet_id), None)
                if snippet and last_paragraph_id:
                    associations[last_paragraph_id].append(snippet)

        return associations




    @staticmethod
    def is_relevant_snippet(paragraph_text, snippet_text):
        """
        Determines if a code snippet is relevant to a paragraph.

        Args:
            paragraph_text (str): Text of the paragraph.
            snippet_text (str): Text of the code snippet.

        Returns:
            bool: True if the snippet is relevant, False otherwise.
        """
        # Simple heuristic: Check if any word in the snippet appears in the paragraph
        paragraph_words = set(paragraph_text.lower().split())
        snippet_words = set(snippet_text.lower().split())
        return not paragraph_words.isdisjoint(snippet_words)


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

        # Normalize semantics
        normalized_paragraphs = []
        with alive_bar(len(enriched_paragraphs), title="Normalizing Semantics") as bar:
            for para in enriched_paragraphs:
                try:
                    # Use BART model for semantic normalization
                    semantics = self.bart_model(para["text"], max_length=130, min_length=30, do_sample=False)[0]["summary_text"]
                    normalized_paragraphs.append({
                        "id": para["id"],
                        "type": para["type"],
                        "text": para["text"],
                        "semantics": semantics,
                        "keywords": para["keywords"],
                        "weight": para["weight"],
                        "sentences": para["sentences"],
                    })
                except Exception as e:
                    print(f"Error normalizing paragraph {para['id']}: {e}")
                finally:
                    bar()

        return {"normalized_paragraphs": normalized_paragraphs}