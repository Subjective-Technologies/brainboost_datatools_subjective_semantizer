import os
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Use the updated Hugging Face embeddings from the new package.
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# We'll use the Transformers pipeline and tokenizer directly.
from transformers import pipeline, AutoTokenizer

def generate_text(prompt, max_new_tokens=128):
    """
    Generates text using a local Hugging Face model.
    
    This function:
      - Loads a text-generation pipeline for a given model (here, distilgpt2).
      - Uses its tokenizer to count the input tokens.
      - Sets the overall max_length to (input tokens + max_new_tokens) so that the model
        has enough room to generate new text.
      - Returns the generated text.
    """
    # Create a text-generation pipeline.
    gen_pipe = pipeline(
        "text-generation",
        model="distilgpt2",      # Change this to another model if desired.
        do_sample=True,
        temperature=0.7,
        truncation=True
    )
    # Load the tokenizer for the model.
    tokenizer = AutoTokenizer.from_pretrained("distilgpt2")
    # Tokenize the prompt to get its length.
    input_ids = tokenizer(prompt, return_tensors="pt").input_ids
    # Set max_length as prompt length + new tokens you want to generate.
    new_max_length = input_ids.shape[1] + max_new_tokens
    # Generate text. (We do not pass max_new_tokens separately; we rely solely on max_length.)
    result = gen_pipe(prompt, max_length=new_max_length)
    return result[0]["generated_text"]

def load_and_split_pdfs(pdf_folder: str):
    """
    Loads all PDFs from the specified folder, attaches metadata,
    and splits them into smaller text chunks.
    """
    documents = []
    
    for filename in os.listdir(pdf_folder):
        if filename.lower().endswith(".pdf"):
            filepath = os.path.join(pdf_folder, filename)
            loader = PyPDFLoader(filepath)
            # Each page is loaded as a separate document.
            docs = loader.load()
            for doc in docs:
                # Attach the source book name as metadata.
                doc.metadata["book"] = filename
            documents.extend(docs)
    
    # Split documents into smaller chunks for finer-grained retrieval.
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    split_docs = text_splitter.split_documents(documents)
    return split_docs

def create_vectorstore_from_docs(documents):
    """
    Creates a FAISS vector store from document chunks using Hugging Face embeddings.
    """
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = FAISS.from_documents(documents, embeddings)
    return vectorstore

def persist_vectorstore(vectorstore, save_path: str):
    """
    Saves the FAISS vector store to the specified directory.
    """
    vectorstore.save_local(save_path)
    print(f"Vector store saved at: {save_path}")

def load_vectorstore(save_path: str):
    """
    Loads the FAISS vector store from the specified directory.
    Note: We allow dangerous deserialization. Ensure you trust the source.
    """
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = FAISS.load_local(save_path, embeddings, allow_dangerous_deserialization=True)
    print(f"Vector store loaded from: {save_path}")
    return vectorstore

def identify_topic(query: str, vectorstore: FAISS) -> str:
    """
    Retrieves the most relevant document chunks based on the query and uses a local LLM
    (via the Transformers pipeline) to determine the best matching topic.
    """
    # Retrieve the top 3 relevant chunks.
    relevant_docs = vectorstore.similarity_search(query, k=3)
    
    # Combine the content of the retrieved chunks.
    context = "\n\n".join(doc.page_content for doc in relevant_docs)
    
    prompt = (
        "The following context is extracted from a set of PDF books, each covering multiple topics. "
        "Each passage may discuss a different subject. Based on the context and the user query, "
        "provide the single topic that best answers the query. "
        "If multiple topics are present, choose the one that directly addresses the query.\n\n"
        f"User Query: {query}\n\n"
        f"Context:\n{context}\n\n"
        "Answer with only a single topic name (or a very short phrase)."
    )
    
    # Call the local text-generation function.
    generated_text = generate_text(prompt, max_new_tokens=128)
    return generated_text.strip()

def main():
    # Set the folder containing PDFs.
    pdf_folder = "com_worktwins_data/books_pdf"
    # Define the path where the FAISS index will be persisted.
    store_path = "faiss_index"
    
    # Check if a persisted vector store already exists.
    if os.path.exists(store_path):
        print("Loading existing vector store...")
        vectorstore = load_vectorstore(store_path)
    else:
        print("No saved vector store found. Processing PDFs and creating new vector store...")
        docs = load_and_split_pdfs(pdf_folder)
        print(f"Loaded and split into {len(docs)} chunks.")
        vectorstore = create_vectorstore_from_docs(docs)
        persist_vectorstore(vectorstore, store_path)
    
    # Get user input.
    user_text = input("Enter your text: ")
    
    # Identify the topic based on the input.
    topic = identify_topic(user_text, vectorstore)
    print("\nInferred Topic:")
    print(topic)

if __name__ == "__main__":
    main()
