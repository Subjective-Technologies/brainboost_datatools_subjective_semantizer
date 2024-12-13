# ParagraphsAndCodeUnifiedPipe.py

import re
import hashlib
from hashlib import sha256
from collections import defaultdict
from alive_progress import alive_bar
from pygments.lexers import guess_lexer, ClassNotFound
import spacy  # For NLP sentence tokenization

from com_worktwins_pipe.Pipe import Pipe
from com_worktwins_pipe.WordFrequenciesPipe import WordFrequenciesPipe
from com_worktwins_languages.Language import Language  # Adjust the import path as necessary

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

class ParagraphsAndCodeUnifiedPipe(Pipe):
    """
    A unified Pipe subclass to extract and interleave paragraphs and source code snippets,
    linking code snippets to the preceding paragraph.
    """
    def run(self, input_data):
        """
        Processes raw text to extract paragraphs and code snippets, interleaving them
        in the output with appropriate links.

        Args:
            input_data (str): The raw text extracted from a document.

        Returns:
            dict: JSON containing a unified list of paragraphs and code snippets.
        """
        raw_text = input_data

        # Access word frequencies from dependencies
        # Assuming the first dependency is WordFrequenciesPipe
        if not self.dependencies:
            raise ValueError("ParagraphsAndCodeUnifiedPipe requires WordFrequenciesPipe as a dependency.")
        
        word_frequencies = self.dependencies[0].load_output()
        word_freq_dict = {item["word"]: item["book_frequency"] for item in word_frequencies}

        # Load programming languages
        language_list = Language.load_languages()
        valid_languages = set(language_list.keys())

        # Regex to detect multi-line code blocks (at least 2 lines of indented code)
        code_block_pattern = re.compile(r'((?:^(?: {4}|\t).+\n?)+)', re.MULTILINE)

        # Split the text into blocks (paragraphs or code snippets)
        blocks = []
        last_index = 0
        for match in code_block_pattern.finditer(raw_text):
            start, end = match.span()
            # Text before the code block
            if start > last_index:
                paragraph_text = raw_text[last_index:start].strip()
                if paragraph_text:
                    blocks.append({"type": "paragraph", "text": paragraph_text})
            # The code block
            code_text = match.group(0).strip('\n')
            if code_text:
                blocks.append({"type": "source_code", "text": code_text})
            last_index = end
        # Remaining text after the last code block
        if last_index < len(raw_text):
            remaining_text = raw_text[last_index:].strip()
            if remaining_text:
                blocks.append({"type": "paragraph", "text": remaining_text})

        unified_report = []
        last_paragraph_id = None
        last_paragraph_keywords = []

        with alive_bar(len(blocks), title="Processing blocks") as bar:
            for block in blocks:
                if block["type"] == "paragraph":
                    paragraph = self.process_paragraph(block["text"], word_freq_dict)
                    unified_report.append(paragraph)
                    last_paragraph_id = paragraph["id"]
                    last_paragraph_keywords = paragraph["keywords"]
                elif block["type"] == "source_code":
                    code_snippet = self.process_code_snippet(
                        block["text"], 
                        valid_languages, 
                        last_paragraph_id,
                        last_paragraph_keywords
                    )
                    unified_report.append(code_snippet)
                bar()

        # Additionally, handle inline code snippets (e.g., surrounded by backticks)
        inline_code_pattern = re.compile(r'`([^`]+)`')
        inline_codes = inline_code_pattern.findall(raw_text)
        for code in inline_codes:
            code_id = hashlib.md5(code.encode("utf-8")).hexdigest()[:8]
            code_snippet = {
                "id": code_id,
                "type": "source_code",
                "text": code,
                "programming_language": "unknown",  # Optionally infer language
                "weight": 0.0,
                "linked_paragraph_id": last_paragraph_id
            }
            unified_report.append(code_snippet)

        return {"unified_report": unified_report}

    def process_paragraph(self, paragraph_text, word_freq_dict):
        """
        Processes a paragraph: tokenizes into sentences, extracts keywords, and enriches with metadata.

        Args:
            paragraph_text (str): The text of the paragraph.
            word_freq_dict (dict): Dictionary of word frequencies.

        Returns:
            dict: Enriched paragraph data.
        """
        paragraph_id = sha256(paragraph_text.encode()).hexdigest()[:8]

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

        return {
            "id": paragraph_id,
            "type": "paragraph",
            "text": paragraph_text,
            "keywords": sorted(paragraph_keywords),
            "weight": 0.0,
            "sentences": sentences,
        }

    def process_code_snippet(self, code_text, valid_languages, linked_paragraph_id, linked_paragraph_keywords):
        """
        Processes a code snippet: detects programming language and enriches with metadata.

        Args:
            code_text (str): The text of the code snippet.
            valid_languages (set): Set of valid programming languages.
            linked_paragraph_id (str): ID of the paragraph to link this code snippet to.
            linked_paragraph_keywords (list): Keywords from the linked paragraph.

        Returns:
            dict: Enriched code snippet data.
        """
        # Attempt to guess the language
        try:
            lexer = guess_lexer(code_text)
            lang = lexer.name if lexer.name in valid_languages else "unknown"
        except ClassNotFound:
            lang = "unknown"

        if lang == "unknown" and linked_paragraph_keywords:
            # Infer language from linked paragraph keywords
            language_mapping = {
                "python": "Python",
                "java": "Java",
                "javascript": "JavaScript",
                "c++": "C++",
                "ruby": "Ruby",
                "go": "Go",
                # Add more mappings as needed
            }
            for keyword in linked_paragraph_keywords:
                if keyword.lower() in language_mapping:
                    lang = language_mapping[keyword.lower()]
                    break

        # Generate hash
        code_id = hashlib.md5(code_text.encode("utf-8")).hexdigest()[:8]

        return {
            "id": code_id,
            "type": "source_code",
            "text": code_text,
            "programming_language": lang,
            "weight": 0.0,
            "linked_paragraph_id": linked_paragraph_id
        }
