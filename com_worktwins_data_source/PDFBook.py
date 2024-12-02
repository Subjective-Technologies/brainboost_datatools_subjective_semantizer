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
import unicodedata
import json
import re
import fitz  # PyMuPDF
from com_worktwins_languages.Language import Language
from transformers import pipeline
import torch



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

    def split_into_paragraphs(self, raw_text):
        """
        Split raw text into paragraphs based on double newline separation and exclude paragraphs containing source code.
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

    def generate_frequencies(self, paragraphs):
        """
        Generate word frequencies and related data from the paragraphs.
        """
        # Split text into paragraphs and generate paragraph IDs
        word_counts = defaultdict(int)
        word_paragraph_map = defaultdict(set)

        with alive_bar(len(paragraphs), title="Processing paragraphs") as bar:
            for para in paragraphs:
                pid = para["id"]
                text = para["text"]
                words = [word.lower() for word in text.split() if word.isalnum()]
                for word in words:
                    word_counts[word] += 1
                    word_paragraph_map[word].add(pid)
                bar()

        # Create a DataFrame for book word frequencies
        book_freq_df = pd.DataFrame(
            [(word, count, list(word_paragraph_map[word])) for word, count in word_counts.items()],
            columns=["word", "book_frequency", "paragraphs"],
        )

        # Add English language frequencies
        book_freq_df["english_frequency"] = book_freq_df["word"].apply(lambda word: word_frequency(word, "en"))

        # Exclude connector words based on thresholds
        english_top_threshold = book_freq_df["english_frequency"].quantile(ENGLISH_TOP_PERCENTILE)
        book_top_threshold = book_freq_df["book_frequency"].quantile(BOOK_TOP_PERCENTILE)

        excluded_words = book_freq_df[
            (book_freq_df["english_frequency"] >= english_top_threshold) &
            (book_freq_df["book_frequency"] >= book_top_threshold)
        ]

        book_freq_df = book_freq_df[~book_freq_df["word"].isin(excluded_words["word"])]

        # Sorting
        book_freq_df = book_freq_df.sort_values(by=["book_frequency", "english_frequency"], ascending=[False, True])
        english_freq_df = book_freq_df[["word", "english_frequency"]].sort_values(by="english_frequency", ascending=True)

        return book_freq_df, english_freq_df

    def process_paragraphs(self, paragraphs, book_freq_df):
        """
        Process paragraphs into sentences and generate enriched data.
        """
        book_freq_dict = book_freq_df.set_index("word")["book_frequency"].to_dict()

        enriched_paragraphs = []
        with alive_bar(len(paragraphs), title="Processing sentences") as bar:
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
                    keywords = [word for word in words if word in book_freq_dict]

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

    def extract_code_snippets_v2(self, text):
        """
        Enhanced extraction of code snippets with dynamic fallback based on book context.
        """
        import hashlib
        from collections import defaultdict
        import re
        from pygments.lexers import guess_lexer, ClassNotFound
        from com_worktwins_languages.Language import Language

        def generate_hash(code_snippet):
            return hashlib.md5(code_snippet.encode('utf-8')).hexdigest()

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
                "id": generate_hash(code),
                "type": "source_code",
                "text": code,
                "programming_language": lang,
                "weight": 0.0
            })

        return snippet_list

    def extract_semantics(self, enriched_paragraphs):
        """
        Normalize the knowledge of the book semantically using BART, outputting to a 'semantics' field.
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
                        "semantics": semantics,  # Renamed field
                        "keywords": para["keywords"],
                        "weight": para["weight"],
                        "sentences": para["sentences"],
                    })
                except Exception as e:
                    print(f"Error normalizing paragraph {para['id']}: {e}")
                finally:
                    bar()

        return normalized_paragraphs

    def generate_semantic_tree(self, normalized_paragraphs, book_freq_dict, english_freq_dict):
        """
        Generate a semantic tree from normalized paragraphs based on keywords.
        """
        def generate_hash_from_keywords_with_frequency(keywords):
            """
            Generate a unique ID for a semantic unit based on keyword frequencies.
            """
            enriched_keywords = [
                {
                    "word": keyword,
                    "book_freq": book_freq_dict.get(keyword, 0),
                    "english_freq": english_freq_dict.get(keyword, float('inf')),
                }
                for keyword in keywords
            ]

            # Sort by book frequency (desc), then by English frequency (asc)
            enriched_keywords.sort(key=lambda x: (-x["book_freq"], x["english_freq"]))

            # Weighted sum to ensure order independence
            sum_value = sum(
                (index + 1) * (data["book_freq"] - data["english_freq"])
                for index, data in enumerate(enriched_keywords)
            )
            return sha256(str(sum_value).encode("utf-8")).hexdigest()[:8]

        semantic_tree = {}
        with alive_bar(len(normalized_paragraphs), title="Generating Semantic Tree") as bar:
            for para in normalized_paragraphs:
                keywords = para.get("keywords", [])
                if not keywords:
                    bar()
                    continue

                # Generate a semantic unit ID
                unit_id = generate_hash_from_keywords_with_frequency(keywords)
                parent_id = None

                # Add unit to the tree
                current_node = semantic_tree
                for word in sorted(keywords):  # Hierarchy by sorted keywords
                    word_hash = sha256(word.encode("utf-8")).hexdigest()[:8]
                    if word_hash not in current_node:
                        current_node[word_hash] = {
                            "id": word_hash,
                            "word": word,
                            "children": {},
                        }
                    current_node = current_node[word_hash]["children"]
                    parent_id = word_hash  # Track the last parent node ID

                # Assign paragraph data to the final node
                current_node["unit"] = {
                    "id": unit_id,
                    "parent_id": parent_id,
                    "semantics": para.get("semantics"),
                    "keywords": keywords,
                    "text": para.get("text"),
                }
                bar()

        return semantic_tree
    
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



    def evaluate(self, keywords):
        """
        Evaluate the semantic tree to find topics based on keywords.
        """
        # Load the semantic tree
        semantic_tree_path = os.path.join(self.output_dir, f"{self.name}_semantic_tree.json")
        if not os.path.exists(semantic_tree_path):
            raise FileNotFoundError(f"Semantic tree file not found: {semantic_tree_path}")

        with open(semantic_tree_path, "r", encoding="utf-8") as f:
            semantic_tree = json.load(f)

        # Generate the target ID based on the keywords
        target_id = self.generate_semantic_unit_id(keywords)

        # Perform a direct lookup in the semantic tree
        matched_unit = semantic_tree.get(target_id)

        if matched_unit:
            return {
                "id": target_id,
                "semantics": matched_unit.get("semantics"),
                "keywords": matched_unit.get("keywords"),
                "children": matched_unit.get("children"),
            }
        else:
            return {"error": "No matching topic found for the provided keywords."}



    def save_to_txt(self,data, output_path):
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(data)


    def save_to_json(self,data, output_path):
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)



    def to_knowledge_hooks(self):
        """
        Generate all knowledge hooks for the book and save the results.
        """
        raw_text = self.extract_raw()
        self.save_to_txt(raw_text, os.path.join(self.output_dir, f"{self.name}.txt"))

        # Paragraphs
        paragraphs = self.split_into_paragraphs(raw_text)
        self.save_to_json(paragraphs, os.path.join(self.output_dir, f"{self.name}_paragraphs.json"))

        # Frequencies
        book_freq_df, english_freq_df = self.generate_frequencies(paragraphs)
        self.save_to_json(book_freq_df.to_dict(orient="records"), os.path.join(self.output_dir, f"{self.name}_book_frequencies.json"))
        self.save_to_json(english_freq_df.to_dict(orient="records"), os.path.join(self.output_dir, f"{self.name}_english_frequencies.json"))

        # Enriched paragraphs
        enriched_paragraphs = self.process_paragraphs(paragraphs, book_freq_df)
        self.save_to_json(enriched_paragraphs, os.path.join(self.output_dir, f"{self.name}_enriched_paragraphs.json"))

        # Source code
        code_blocks = self.extract_code_snippets_v2(raw_text)
        self.save_to_json(code_blocks, os.path.join(self.output_dir, f"{self.name}_source_code.json"))

        # Semantic normalization
        normalized_paragraphs = self.extract_semantics(enriched_paragraphs)
        self.save_to_json(normalized_paragraphs, os.path.join(self.output_dir, f"{self.name}_semantically_normalized.json"))

        # Semantic tree
        semantic_tree = self.generate_semantic_tree(normalized_paragraphs, 
                                                    book_freq_df.set_index("word")["book_frequency"].to_dict(),
                                                    english_freq_df.set_index("word")["english_frequency"].to_dict())
        self.save_to_json(semantic_tree, os.path.join(self.output_dir, f"{self.name}_semantic_tree.json"))





