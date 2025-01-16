import os
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.llms import OpenAI

# STEP 1: Load all PDFs from a folder and split them into chunks.
def load_and_split_pdfs(pdf_folder: str):
    documents = []
    for filename in os.listdir(pdf_folder):
        if filename.lower().endswith(".pdf"):
            filepath = os.path.join(pdf_folder, filename)
            loader = PyPDFLoader(filepath)
            # load the pages of the PDF; each page is a document.
            docs = loader.load()  
            # Optionally, you can add metadata such as the book title (from filename)
            for doc in docs:
                doc.metadata["book"] = filename  # the book from which this chunk comes
            documents.extend(docs)
    
    # Now, split the documents into smaller chunks for finer-grained retrieval.
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    split_docs = text_splitter.split_documents(documents)
    return split_docs

# STEP 2: Create a FAISS vector store from the document chunks.
def create_vectorstore_from_docs(documents):
    embeddings = OpenAIEmbeddings()  # Ensure you have OPENAI_API_KEY set in your environment.
    vectorstore = FAISS.from_documents(documents, embeddings)
    return vectorstore

# STEP 3: Use an LLM chain to infer the best matching topic.
def identify_topic(query: str, vectorstore: FAISS) -> str:
    # Retrieve the top k (e.g., 3) relevant chunks.
    relevant_docs = vectorstore.similarity_search(query, k=3)
    
    # Combine the content of the retrieved chunks.
    context = "\n\n".join(doc.page_content for doc in relevant_docs)
    
    # Build a prompt that informs the LLM about the multi-topic nature of the books.
    prompt = (
        "The documents below come from books that cover multiple topics. "
        "Each passage may discuss a different subject. Based solely on the context given "
        "and the user query, determine the name of the most relevant topic. "
        "If the context is mixed, choose the topic that most directly addresses the user query.\n\n"
        f"User Query: {query}\n\n"
        f"Context:\n{context}\n\n"
        "Answer with just a single topic name (or a very short phrase)."
    )
    
    llm = OpenAI(temperature=0)
    topic = llm(prompt)
    return topic.strip()

def main():
    # Specify the folder where your PDFs are stored.
    pdf_folder = "com_worktwins_data/books_pdf"  # <-- change this to your actual folder path
    
    print("Loading and splitting PDF documents...")
    docs = load_and_split_pdfs(pdf_folder)
    print(f"Loaded and split into {len(docs)} chunks.")
    
    print("Creating vector store from document chunks...")
    vectorstore = create_vectorstore_from_docs(docs)
    
    # Get user input text
    user_text = input("Enter your text: ")
    
    # Use the LLM chain to infer the best topic.
    topic = identify_topic(user_text, vectorstore)
    print("\nInferred Topic:")
    print(topic)

if __name__ == "__main__":
    main()
