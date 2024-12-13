import os
from com_worktwins_data_source.PDFBook import PDFBook

PDF_DIR = "com_worktwins_data/books_pdf"

def main():
    PDF_DIR = "com_worktwins_data/books_pdf"
    keywords = ["if", "while", "for", "sum"]  # Example keywords

    for file_name in ["/brainboost/brainboost_data/data_tools/brainboost_datatools_subjective_semantizer/com_worktwins_data/books_pdf/Bruce Eckel - Thinking in Java 4th Edition.pdf"]:
        if file_name.endswith(".pdf"):
            pdf_path = os.path.join(PDF_DIR, file_name)
            print(f"Processing {file_name}...")
            book = PDFBook(pdf_path)

            # Generate knowledge hooks
            book.to_knowledge_hooks()

            # Evaluate with keywords
            print(f"Evaluating book for keywords: {keywords}")
            topics = book.evaluate(keywords)

            print("Evaluation Results:")
            if not topics:
                print("No topics matched the given keywords.")
            else:
                for topic in topics:
                    print(f"ID: {topic['id']}")
                    print(f"Path: {topic['path']}")
                    print(f"Semantics: {topic['semantics']}")
                    print(f"Relevance Score: {topic['relevance_score']:.2f}")
                    print("-----------")

    print("Processing complete.")


if __name__ == "__main__":
    main()