import os
from typing import List, Dict, Any
import pymupdf  # Updated to use direct pymupdf instead of deprecated fitz alias
from langchain_core.documents import Document

class DocumentIngestionPipeline:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir

    def load_documents(self) -> List[Document]:
        """Loads documents from directory and extracts text with page-level metadata."""
        documents = []
        
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            return documents

        for file_name in os.listdir(self.data_dir):
            file_path = os.path.join(self.data_dir, file_name)
            
            if file_name.endswith(".pdf"):
                docs = self._parse_pdf(file_path, file_name)
                documents.extend(docs)
            elif file_name.endswith(".txt"):
                docs = self._parse_txt(file_path, file_name)
                documents.extend(docs)
                
        return documents

    def _parse_pdf(self, file_path: str, file_name: str) -> List[Document]:
        """Parses PDF file page by page to retain accurate page numbers for citations."""
        docs = []
        with pymupdf.open(file_path) as pdf:
            for page_num, page in enumerate(pdf):
                text = page.get_text()
                if text.strip():
                    metadata = {
                        "source": file_name,
                        "page": page_num + 1,
                        "file_type": "pdf"
                    }
                    docs.append(Document(page_content=text, metadata=metadata))
        return docs

    def _parse_txt(self, file_path: str, file_name: str) -> List[Document]:
        """Parses plain text files."""
        docs = []
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
            if text.strip():
                metadata = {
                    "source": file_name,
                    "page": 1,
                    "file_type": "txt"
                }
                docs.append(Document(page_content=text, metadata=metadata))
        return docs