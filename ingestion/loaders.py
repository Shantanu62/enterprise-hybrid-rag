
from pathlib import Path

from docx import Document
from pypdf import PdfReader


def load_document(file_path: str) -> list[dict]:
    """
    Extract text from PDF, DOCX, or TXT files.

    Returns a list of records containing text and source metadata.
    PDF records include page numbers.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    extension = path.suffix.lower()
    records = []

    if extension == ".pdf":
        reader = PdfReader(str(path))

        if reader.is_encrypted:
            raise ValueError("Encrypted PDF files are not supported yet.")

        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()

            if text:
                records.append(
                    {
                        "text": text,
                        "metadata": {
                            "source": path.name,
                            "page": page_number,
                            "file_type": "pdf",
                        },
                    }
                )

    elif extension == ".docx":
        document = Document(str(path))

        text = "\n".join(
            paragraph.text.strip()
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        )

        if text:
            records.append(
                {
                    "text": text,
                    "metadata": {
                        "source": path.name,
                        "page": None,
                        "file_type": "docx",
                    },
                }
            )

    elif extension == ".txt":
        text = path.read_text(encoding="utf-8-sig").strip()

        if text:
            records.append(
                {
                    "text": text,
                    "metadata": {
                        "source": path.name,
                        "page": None,
                        "file_type": "txt",
                    },
                }
            )

    else:
        raise ValueError(
            f"Unsupported file type: {extension}. "
            "Supported formats: PDF, DOCX, TXT."
        )

    if not records:
        raise ValueError(
            f"No extractable text found in {path.name}. "
            "The file may be empty, scanned, or image-only."
        )

    return records
