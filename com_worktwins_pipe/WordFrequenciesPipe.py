# WordFrequenciesPipe.py

import json
import logging
from com_worktwins_pipe.Pipe import Pipe  # Import the base Pipe class
from collections import defaultdict
from alive_progress import alive_bar
import re

class WordFrequenciesPipe(Pipe):
    """
    A Pipe subclass to generate word frequencies and related data from raw text.
    """

    def run(self, input_data):
        """
        Generate word frequencies and filter out connector words.

        Args:
            input_data (str): Raw text extracted from the PDF.

        Returns:
            list: JSON-compatible list of words with frequencies.
        """
        word_frequencies = WordFrequenciesPipe.generate_frequencies(raw_text=input_data)

        return word_frequencies

    @staticmethod
    def generate_frequencies(raw_text):
        """
        Generate word frequencies and related data directly from raw text.

        Args:
            raw_text (str): Raw text extracted from a document.

        Returns:
            list: Combined frequencies sorted by book_frequency descending and english_frequency ascending.
        """
        try:
            from collections import defaultdict
            import pandas as pd
            from wordfreq import word_frequency
            from alive_progress import alive_bar

            ENGLISH_TOP_PERCENTILE = 0.9  # Top 10% of English frequency
            BOOK_TOP_PERCENTILE = 0.9  # Top 10% of book frequency

            word_counts = defaultdict(int)
            word_paragraph_map = defaultdict(set)

            # Split text into paragraphs (based on double newlines)
            paragraphs = raw_text.split("\n\n")

            # Count word occurrences and map them to paragraphs
            with alive_bar(len(paragraphs), title="Processing paragraphs") as bar:
                for idx, para in enumerate(paragraphs):
                    para = para.strip()
                    if not para:
                        continue

                    # Use regex to find words, ignoring punctuation
                    words = re.findall(r'\b\w+\b', para.lower())
                    for word in words:
                        word_counts[word] += 1
                        word_paragraph_map[word].add(idx)
                    bar()

            # Create a DataFrame for book word frequencies
            book_freq_df = pd.DataFrame(
                [(word, count, list(word_paragraph_map[word])) for word, count in word_counts.items()],
                columns=["word", "book_frequency", "paragraphs"],
            )

            # Add English language frequencies using wordfreq
            book_freq_df["english_frequency"] = book_freq_df["word"].apply(lambda word: word_frequency(word, "en"))

            # Exclude connector words based on thresholds
            english_top_threshold = book_freq_df["english_frequency"].quantile(ENGLISH_TOP_PERCENTILE)
            book_top_threshold = book_freq_df["book_frequency"].quantile(BOOK_TOP_PERCENTILE)

            excluded_words = book_freq_df[
                (book_freq_df["english_frequency"] >= english_top_threshold) &
                (book_freq_df["book_frequency"] >= book_top_threshold)
            ]

            # Filter out excluded words
            book_freq_df = book_freq_df[~book_freq_df["word"].isin(excluded_words["word"])]

            # Sorting: book_frequency descending, english_frequency ascending
            combined_freq_df = book_freq_df.sort_values(by=["book_frequency", "english_frequency"], ascending=[False, True])

            # Convert to JSON-compatible list
            combined_frequencies = combined_freq_df[["word", "book_frequency", "english_frequency"]].to_dict(orient="records")

            return combined_frequencies

        except Exception as e:
            # Handle unexpected errors gracefully
            logging.error(f"Error generating frequencies: {e}")
            return []
