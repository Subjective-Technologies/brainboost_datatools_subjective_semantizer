import fitz  # PyMuPDF
from transformers import AutoModelForCausalLM, AutoTokenizer
import json
import os

# Paths
PDF_PATH = "com_worktwins_data/books_pdf/Scott Chacon - Pro Git.pdf"
EXTRACTED_TEXT_PATH = "git1.txt"
KNOWLEDGE_HOOKS_OUTPUT_PATH = "knowledgehooks.json"
RAW_OUTPUT_PATH = "raw_outputs.json"
LLAMA_MODEL_PATH = "/home/golden/.llama/checkpoints/Llama3.2-3B-Instruct-HF"
TEMP_PROGRESS_FILE = "progress.json"  # Temporary file to save progress
CHUNK_SIZE = 1000  # Characters per chunk to feed into the model


def extract_text_from_pdf(pdf_path, output_path):
    """
    Extracts text from a PDF and saves it to a text file.
    """
    with fitz.open(pdf_path) as pdf:
        text_content = []
        for page_num in range(pdf.page_count):
            page = pdf[page_num]
            text = page.get_text("text")
            text_content.append(text)
            print(f"Extracted text from page {page_num + 1}/{pdf.page_count}")

    with open(output_path, "w", encoding="utf-8") as output_file:
        output_file.write("\n\n".join(text_content))

    print(f"Text extracted and saved to {output_path}")
    return "\n\n".join(text_content)


def generate_knowledge_hooks(
    text, model_path, output_path, raw_output_path, temp_progress_file
):
    """
    Generate knowledge hooks from the provided text using a language model.
    """
    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(model_path)

    # Split the text into manageable chunks
    def split_text_into_chunks(text, max_chunk_size=512):
        """
        Split text into chunks of manageable size for the model.
        """
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0

        for word in words:
            word_length = len(word) + 1  # Account for space
            if current_length + word_length <= max_chunk_size:
                current_chunk.append(word)
                current_length += word_length
            else:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = word_length

        if current_chunk:
            chunks.append(" ".join(current_chunk))
        return chunks

    chunks = split_text_into_chunks(text)
    knowledge_hooks = []
    raw_outputs = []

    # Resume progress if a temporary file exists
    if os.path.exists(temp_progress_file):
        with open(temp_progress_file, "r") as f:
            progress_data = json.load(f)
            start_chunk = progress_data.get("last_processed_chunk", 0)
            print(f"Resuming from chunk {start_chunk + 1}/{len(chunks)}...")
    else:
        start_chunk = 0
        print("No previous progress found. Starting fresh.")

    # Process each chunk
    for i, chunk in enumerate(chunks[start_chunk:], start=start_chunk):
        print(f"Processing chunk {i + 1}/{len(chunks)}...")
        prompt = (
            "Generate a JSON array of knowledge hooks from the following text. Each knowledge hook should include:\n"
            "1. 'description': A concise summary of the main idea.\n"
            "2. 'keywords': Relevant keywords.\n"
            "Format the output as a JSON array.\n\n"
            f"Text:\n{chunk}"
        )

        inputs = tokenizer(prompt, return_tensors="pt", truncation=True)
        outputs = model.generate(**inputs, max_length=512, temperature=0.7, do_sample=True)

        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        raw_outputs.append(generated_text)

        try:
            hooks = json.loads(generated_text)
            if isinstance(hooks, list):
                knowledge_hooks.extend(hooks)
            else:
                print(f"Chunk {i + 1} did not generate a valid JSON array. Skipping...")
        except json.JSONDecodeError:
            print(f"Chunk {i + 1} generated invalid JSON. Skipping...")

        # Save progress to the temporary file
        with open(temp_progress_file, "w") as f:
            json.dump({"last_processed_chunk": i}, f)

    # Save final outputs and remove the temporary progress file
    with open(output_path, "w") as f:
        json.dump(knowledge_hooks, f, indent=4)

    with open(raw_output_path, "w") as f:
        json.dump(raw_outputs, f, indent=4)

    print(f"Knowledge hooks saved to {output_path}")
    print(f"Raw model outputs saved to {raw_output_path}")

    if os.path.exists(temp_progress_file):
        os.remove(temp_progress_file)  # Clean up after completion
        print(f"Temporary progress file {temp_progress_file} removed.")


if __name__ == "__main__":
    # Step 1: Extract text or load existing text file
    if not os.path.exists(EXTRACTED_TEXT_PATH):
        print(f"File {EXTRACTED_TEXT_PATH} not found. Extracting text from the PDF...")
        extracted_text = extract_text_from_pdf(PDF_PATH, EXTRACTED_TEXT_PATH)
    else:
        print(f"Found existing {EXTRACTED_TEXT_PATH}. Skipping text extraction.")
        with open(EXTRACTED_TEXT_PATH, "r", encoding="utf-8") as f:
            extracted_text = f.read()

    # Step 2: Generate knowledge hooks from the extracted text
    generate_knowledge_hooks(
        extracted_text,
        LLAMA_MODEL_PATH,
        KNOWLEDGE_HOOKS_OUTPUT_PATH,
        RAW_OUTPUT_PATH,
        TEMP_PROGRESS_FILE,
    )
