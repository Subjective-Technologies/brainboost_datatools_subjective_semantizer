import pytest
from com_worktwins_data_source.PDFBook import PDFBook

PDF_PATH = "com_worktwins_data/books_pdf/Scott Chacon - Pro Git.pdf"


@pytest.fixture
def sample_pdf():
    """
    Use the provided PDF for testing.
    """
    return PDF_PATH


def test_pdfbook_initialization(sample_pdf):
    """
    Test that PDFBook initializes correctly with a valid PDF file.
    """
    book = PDFBook(sample_pdf)
    assert book.text is not None
    assert "Git" in book.text  # Expecting 'Git' to be present in the extracted text




def test_pdfbook_invalid_path():
    """
    Test that PDFBook raises a FileNotFoundError when initialized with an invalid path.
    """
    invalid_path = "non_existent_file.pdf"
    with pytest.raises(FileNotFoundError):
        PDFBook(invalid_path)
