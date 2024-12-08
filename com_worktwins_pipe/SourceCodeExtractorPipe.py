import re
import hashlib
from collections import defaultdict
from pygments.lexers import guess_lexer, ClassNotFound
from com_worktwins_languages.Language import Language
from com_worktwins_pipe.Pipe import Pipe  # Import the base Pipe class

class SourceCodeExtractorPipe(Pipe):
    """
    A Pipe subclass to extract source code snippets from text and determine their programming languages.
    """
    def run(self, input_data):
        """
        Extracts source code snippets from raw text.

        Args:
            input_data (dict): Input JSON containing "raw_text".

        Returns:
            dict: JSON containing a list of extracted code snippets with metadata.
        """

        code_snippets = self.extract_code_snippets_v2(input_data)
        return {"code_snippets": code_snippets}

    @staticmethod
    def extract_code_snippets_v2(text):
        """
        Enhanced extraction of code snippets with dynamic fallback based on book context.

        Args:
            text (str): The raw text extracted from a document.

        Returns:
            list: A list of dictionaries, each representing a code snippet with metadata.
        """
        # Load the list of programming languages
        language_list = Language.load_languages()
        valid_languages = set(language_list.keys())  # Get all language names

        # Count standalone occurrences of programming languages in the text
        def count_standalone_occurrences(word, text):
            pattern = rf'\b{re.escape(word)}\b'
            return len(re.findall(pattern, text, re.IGNORECASE))

        language_occurrences = defaultdict(int)
        for language in valid_languages:
            count = count_standalone_occurrences(language, text)
            if count > 0:
                language_occurrences[language] += count

        # Determine the most frequent language in the book
        most_frequent_language = max(language_occurrences, key=language_occurrences.get, default="unknown")

        # Regex to detect multi-line code blocks (at least 2 lines of indented code)
        code_block_pattern = re.compile(r'((?:^(?: {4}|\t).+\n)+)', re.MULTILINE)
        snippet_list = []
        language_frequencies = defaultdict(int)

        # Process snippets and detect languages
        for match in code_block_pattern.finditer(text):
            code = match.group(0).strip()

            # Attempt to guess the language
            try:
                lexer = guess_lexer(code)
                lang = lexer.name if lexer.name in valid_languages else "unknown"
            except ClassNotFound:
                lang = "unknown"

            # Update language frequencies
            if lang != "unknown":
                language_frequencies[lang] += 1
            else:
                lang = most_frequent_language  # Default to the most frequent language in the book

            # Generate hash and add snippet
            snippet_list.append({
                "id": hashlib.md5(code.encode("utf-8")).hexdigest(),
                "type": "source_code",
                "text": code,
                "programming_language": lang,
                "weight": 0.0
            })

        return snippet_list
