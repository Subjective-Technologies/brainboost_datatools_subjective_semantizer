import os
from hashlib import sha256
from alive_progress import alive_bar
from com_worktwins_pipe.Pipe import Pipe  # Import the base Pipe class

class SemanticTreePipe(Pipe):
    """
    A Pipe subclass to generate a semantic tree from normalized paragraphs.
    """
    def run(self, input_data):
        """
        Generates a semantic tree from normalized paragraphs based on keywords.

        Args:
            input_data (dict): Input JSON containing "normalized_paragraphs", "book_frequencies", and "english_frequencies".

        Returns:
            dict: JSON representing the semantic tree.
        """
        normalized_paragraphs = input_data.get("normalized_paragraphs", [])
        book_freq = input_data.get("book_frequencies", [])
        english_freq = input_data.get("english_frequencies", [])

        # Convert frequencies to dictionaries for quick lookups
        book_freq_dict = {item["word"]: item["book_frequency"] for item in book_freq}
        english_freq_dict = {item["word"]: item["english_frequency"] for item in english_freq}

        # Generate the semantic tree
        semantic_tree = self.generate_semantic_tree(normalized_paragraphs, book_freq_dict, english_freq_dict)
        return {"semantic_tree": semantic_tree}

    def generate_semantic_tree(self, normalized_paragraphs, book_freq_dict, english_freq_dict):
        """
        Generate a semantic tree from normalized paragraphs based on keywords.

        Args:
            normalized_paragraphs (list): List of dictionaries with normalized paragraphs.
            book_freq_dict (dict): Dictionary of book word frequencies.
            english_freq_dict (dict): Dictionary of English word frequencies.

        Returns:
            dict: A semantic tree structure with hierarchical relationships between keywords.
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
