import os
from typing import List, Tuple
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings  # You can use other embedding models if needed


class SemanticSimilaritySearch:
    def __init__(self, folder_path: str, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the SemanticSimilaritySearch class.

        Args:
            folder_path (str): Path to the folder containing PDF files.
            chunk_size (int): Size of the text chunks for processing.
            chunk_overlap (int): Overlap size between consecutive text chunks.
        """
        self.folder_path = folder_path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.documents = []
        self.vectorstore = None

    def load_pdfs(self):
        """
        Load and process all PDF files in the specified folder.
        """
        pdf_files = [f for f in os.listdir(self.folder_path) if f.endswith('.pdf')]
        text_splitter = CharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)

        for pdf_file in pdf_files:
            file_path = os.path.join(self.folder_path, pdf_file)
            loader = PyPDFLoader(file_path)
            pdf_docs = loader.load()
            for pdf_doc in pdf_docs:
                chunks = text_splitter.split_text(pdf_doc.page_content)
                self.documents.extend(chunks)

    def build_vectorstore(self):
        """
        Build the vector store for semantic search.
        """
        if not self.documents:
            raise ValueError("No documents found. Please load PDFs first.")
        
        embeddings = OpenAIEmbeddings()  # Replace with other embeddings if preferred
        self.vectorstore = FAISS.from_texts(self.documents, embeddings)

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Search for semantically similar text across the loaded PDFs.

        Args:
            query (str): Search query.
            top_k (int): Number of top results to return.

        Returns:
            List[Tuple[str, float]]: List of tuples containing matched text and similarity score.
        """
        if not self.vectorstore:
            raise ValueError("Vector store not built. Please build the vector store first.")

        results = self.vectorstore.similarity_search_with_score(query, k=top_k)
        return [(text, score) for text, score in results]


# Example usage:
if __name__ == "__main__":
    folder_path = "path/to/pdf/folder"  # Replace with the path to your folder containing PDFs
    search_tool = SemanticSimilaritySearch(folder_path)
    
    # Step 1: Load and process PDFs
    search_tool.load_pdfs()
    
    # Step 2: Build the vector store
    search_tool.build_vectorstore()
    
    # Step 3: Perform a search
    query = "Enter your search query here"
    results = search_tool.search(query)
    
    # Display results
    for text, score in results:
        print(f"Text: {text}\nScore: {score}\n")
