import fitz  # PyMuPDF
import os
from alive_progress import alive_bar



class PDFBook:
    def __init__(self, pdf_path):
        """
        Initialize the PDFBook class with the path to a PDF file.
        """
        self.pdf_path = pdf_path

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


    def extract_normalized(self):
        """
        Extract normalized text from the PDF.
        """

        @staticmethod
        def clean_text(text):
            """
            Clean the extracted text by removing non-alphanumeric characters and excess whitespace.
            """
            text = text.replace("\n", " ").strip()
            text = " ".join(word for word in text.split() if word.isalnum())
            return text


        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(f"The file {self.pdf_path} does not exist.")

        with fitz.open(self.pdf_path) as pdf:
            text_content = []
            total_pages = pdf.page_count
            with alive_bar(total_pages, title="Extracting Normalized Text") as bar:
                for page_num in range(total_pages):
                    page = pdf[page_num]
                    text = page.get_text("text")
                    cleaned_text = clean_text(text)
                    text_content.append(cleaned_text)
                    bar()

        return "\n\n".join(text_content)


    def extract_blocks_as_python_script(self, code_blocks, output_path):
        """
        Save the extracted code blocks to a Python script file using triple quotes for readability.
        """
        with open(output_path, "w", encoding="utf-8") as f:
            for idx, block in enumerate(code_blocks):
                f.write(f"# Code Block {idx + 1}\n")
                f.write(f"'''\n{block}\n'''\n\n")
        print(f"Saved code blocks as Python script to {output_path}")


    def extract_code_blocks(self):
        """
        Extract source code blocks from the PDF text based on refined patterns.
        """
        def is_code_line(line):
            """
            Determine if a line is likely part of source code based on patterns.
            """
            code_keywords = ["class", "public", "private", "protected", "void", "static", "int", "new", "import", "package"]
            code_symbols = ["{", "}", "(", ")", ";", "=", "<", ">", "[", "]", "//", "/*", "*/", "@"]

            # Lines with significant indentation or code symbols
            return (
                line.strip().startswith(" ") or line.strip().startswith("\t") or
                any(keyword in line for keyword in code_keywords) or
                any(symbol in line for symbol in code_symbols)
            )
        
        def is_valid_code_block(block):
            """
            Determine if a block of text is likely to be valid source code.
            """
            lines = block.split("\n")
            # Discard short blocks
            if len(lines) < 3:
                return False
            # Check if at least one line contains clear code structure
            return any(is_code_line(line) for line in lines)

        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(f"The file {self.pdf_path} does not exist.")

        code_blocks = []
        with fitz.open(self.pdf_path) as pdf:
            total_pages = pdf.page_count
            with alive_bar(total_pages, title="Extracting Code Blocks") as bar:
                for page_num in range(total_pages):
                    page = pdf[page_num]
                    text = page.get_text("text")  # Extract raw text
                    lines = text.splitlines()

                    # Identify potential code blocks
                    current_block = []
                    for line in lines:
                        if is_code_line(line):
                            current_block.append(line)
                        elif current_block:
                            # End of a code block
                            block_text = "\n".join(current_block).strip()
                            if is_valid_code_block(block_text):
                                code_blocks.append(block_text)
                            current_block = []

                    # Add the last block if present
                    if current_block:
                        block_text = "\n".join(current_block).strip()
                        if is_valid_code_block(block_text):
                            code_blocks.append(block_text)
                    bar()

        return code_blocks


