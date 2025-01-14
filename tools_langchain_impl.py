import json
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

# Load JSON Data
def load_data(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    documents = []
    for book, content in data.items():
        for entry in content:
            paragraph = entry["paragraph"]
            metadata = {"book": book, "type": "paragraph"}
            documents.append(Document(page_content=paragraph, metadata=metadata))
            for sentence in entry["sentences"]:
                metadata = {"book": book, "type": "sentence"}
                documents.append(Document(page_content=sentence, metadata=metadata))
    return documents

# Build FAISS Index
def build_index(documents):
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(documents, embeddings)
    return vectorstore

# Perform Search
def semantic_search(vectorstore, query, k=5):
    results = vectorstore.similarity_search(query, k=k)
    return results

# Main Function
def main(json_file, query):
    documents = load_data(json_file)
    vectorstore = build_index(documents)
    results = semantic_search(vectorstore, query)
    print("Results:")
    for result in results:
        print(f"Content: {result.page_content}")
        print(f"Metadata: {result.metadata}")





import json
import os
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS

# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

# Function to split text into chunks
def split_text_into_chunks(text, chunk_size=500, chunk_overlap=50):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " "]
    )
    chunks = text_splitter.split_text(text)
    return chunks

# Process PDF into JSON structure
def process_pdf_to_json(pdf_path, output_json_path):
    text = extract_text_from_pdf(pdf_path)
    chunks = split_text_into_chunks(text)
    paragraphs = []
    for i, chunk in enumerate(chunks):
        sentences = [sentence.strip() for sentence in chunk.split(".") if sentence.strip()]
        paragraphs.append({"paragraph": chunk, "sentences": sentences})
    
    # Save to JSON
    book_name = os.path.basename(pdf_path).replace(".pdf", "")
    json_data = {book_name: paragraphs}
    with open(output_json_path, "w", encoding="utf-8") as json_file:
        json.dump(json_data, json_file, ensure_ascii=False, indent=4)
    print(f"JSON saved to {output_json_path}")
    return json_data

# Build FAISS index for semantic similarity
def build_faiss_index_from_json(json_data):
    documents = []
    for book, content in json_data.items():
        for entry in content:
            paragraph = entry["paragraph"]
            metadata = {"book": book, "type": "paragraph"}
            documents.append(Document(page_content=paragraph, metadata=metadata))
            for sentence in entry["sentences"]:
                metadata = {"book": book, "type": "sentence"}
                documents.append(Document(page_content=sentence, metadata=metadata))
    
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(documents, embeddings)
    return vectorstore

# Perform semantic similarity search
def semantic_search(vectorstore, query, k=5):
    results = vectorstore.similarity_search(query, k=k)
    for result in results:
        print(f"Content: {result.page_content}")
        print(f"Metadata: {result.metadata}")

# Main Function
def main(pdf_path, query):
    json_path = pdf_path.replace(".pdf", ".json")
    json_data = process_pdf_to_json(pdf_path, json_path)
    vectorstore = build_faiss_index_from_json(json_data)
    semantic_search(vectorstore, query)

# Example Usage
if __name__ == "__main__":
    pdf_path = "example.pdf"  # Path to your PDF file
    query = "Explain the concept of relativity."  # Query for semantic search
    main(pdf_path, query)







# Example Usage
if __name__ == "__main__":
    json_file = "books.json"  # Path to your JSON file
    query = "Explain the concept of relativity."
    main(json_file, query)
