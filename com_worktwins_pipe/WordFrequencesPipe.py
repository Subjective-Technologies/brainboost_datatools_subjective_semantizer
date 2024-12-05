import os
import pandas as pd
from collections import defaultdict
from wordfreq import word_frequency
from alive_progress import alive_bar
from com_worktwins_pipe.Pipe import Pipe  # Import the base Pipe class

class WordFrequenciesPipe(Pipe):
    """
    A Pipe subclass to generate word frequencies and related data from paragraphs.
    """
    ENGLISH_TOP_PERCENTILE = 0.9  # Top 10% of English frequency
    BOOK_TOP_PERCENTILE = 0.9  # Top 10% of book frequency

    def run(self, input_data):
        """
        Generate word frequencies and filter out connector words.

        Args:
            input_data (dict): Input JSON containing "paragraphs".

        Returns:
            list: JSON-compatible list of words with frequencies.
        """
        paragraphs = input_data.get("paragraphs", [])
        combined_frequencies = self.generate_frequencies(paragraphs)
        return combined_frequencies

    def generate_frequencies(self, paragraphs):
        """
        Generate word frequencies and related data from the paragraphs.

        Args:
            paragraphs (list): List of paragraph dictionaries, each containing an "id" and "text".

        Returns:
            list: Combined frequencies sorted by book_frequency descending and english_frequency ascending.
        """
        word_counts = defaultdict(int)
        word_paragraph_map = defaultdict(set)

        # Count word occurrences and map them to paragraphs
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
        english_top_threshold = book_freq_df["english_frequency"].quantile(self.ENGLISH_TOP_PERCENTILE)
        book_top_threshold = book_freq_df["book_frequency"].quantile(self.BOOK_TOP_PERCENTILE)

        excluded_words = book_freq_df[
            (book_freq_df["english_frequency"] >= english_top_threshold) &
            (book_freq_df["book_frequency"] >= book_top_threshold)
        ]

        # Filter out excluded words
        book_freq_df = book_freq_df[~book_freq_df["word"].isin(excluded_words["word"])]

        # Sorting
        combined_freq_df = book_freq_df.sort_values(by=["book_frequency", "english_frequency"], ascending=[False, True])

        # Convert to JSON-compatible list
        combined_frequencies = combined_freq_df[["word", "book_frequency", "english_frequency"]].to_dict(orient="records")

        return combined_frequencies
