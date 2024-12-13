# main.py

import os
import argparse
from com_worktwins_data_source.PDFBook import PDFBook
import sys

# ===== CUDA Debugging Enhancements =====

def enable_cuda_launch_blocking():
    """
    Enable CUDA launch blocking to make CUDA operations synchronous.
    This helps in obtaining accurate stack traces for CUDA errors.
    """
    os.environ["CUDA_LAUNCH_BLOCKING"] = "1"

def disable_cuda():
    """
    Disable CUDA by making CUDA devices invisible.
    Forces the pipeline to run on the CPU.
    """
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

# ===== End of CUDA Debugging Enhancements =====

def find_pdfs_in_directory(directory):
    """
    Recursively find all PDF files in the given directory.

    Args:
        directory (str): Path to the directory.

    Returns:
        list: List of absolute paths to PDF files.
    """
    pdf_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_path = os.path.join(root, file)
                pdf_files.append(pdf_path)
    return pdf_files

def parse_arguments():
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Process PDF files to generate knowledge hooks."
    )
    parser.add_argument(
        "-d", "--directories",
        nargs="+",
        help="Root directories to search for PDF files recursively."
    )
    parser.add_argument(
        "-f", "--files",
        nargs="+",
        help="Individual PDF files to process."
    )
    parser.add_argument(
        "--disable-cuda",
        action="store_true",
        help="Disable CUDA and force the pipeline to run on the CPU."
    )
    return parser.parse_args()

def process_pdf(args):
    """
    Process a single PDF file.

    Args:
        args (tuple): Tuple containing (pdf_path, disable_cuda).
    """
    pdf_path, disable_cuda_flag = args
    file_name = os.path.basename(pdf_path)
    print(f"Processing '{file_name}'...")
    
    # If CUDA is to be disabled for this PDF, set the environment variable
    if disable_cuda_flag:
        disable_cuda()
    
    try:
        book = PDFBook(pdf_path)
        book.to_knowledge_hooks()
        print(f"Finished processing '{file_name}'.\n")
    except Exception as e:
        print(f"Error processing '{file_name}': {e}\n")
        # Optionally, log the error to a file for later review
        with open("error_log.txt", "a") as error_file:
            error_file.write(f"Error processing '{file_name}': {e}\n")

def main():
    # ===== Enable CUDA Launch Blocking =====
    enable_cuda_launch_blocking()
    # ========================================
    
    args = parse_arguments()

    pdf_paths = []

    # Collect PDF paths from directories
    if args.directories:
        for directory in args.directories:
            if not os.path.isdir(directory):
                print(f"Warning: '{directory}' is not a valid directory. Skipping.")
                continue
            found_pdfs = find_pdfs_in_directory(directory)
            if not found_pdfs:
                print(f"No PDF files found in directory '{directory}'.")
            pdf_paths.extend(found_pdfs)

    # Collect individual PDF paths
    if args.files:
        for file in args.files:
            if not os.path.isfile(file):
                print(f"Warning: '{file}' is not a valid file. Skipping.")
                continue
            if not file.lower().endswith(".pdf"):
                print(f"Warning: '{file}' is not a PDF file. Skipping.")
                continue
            pdf_paths.append(os.path.abspath(file))

    if not pdf_paths:
        print("No PDF files to process. Exiting.")
        return

    # Remove duplicates and sort the list
    pdf_paths = sorted(list(set(pdf_paths)))

    # Prepare arguments for processing
    # Each PDF will decide based on a flag whether to disable CUDA
    # For simplicity, we'll assume all PDFs use CUDA unless --disable-cuda is specified
    process_args = [(pdf_path, args.disable_cuda) for pdf_path in pdf_paths]

    # Process each PDF file
    for args_tuple in process_args:
        process_pdf(args_tuple)

    print("All processing complete.")

if __name__ == "__main__":
    main()
