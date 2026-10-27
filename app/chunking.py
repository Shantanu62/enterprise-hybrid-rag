from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

class AdvancedChunkingEngine:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Splits raw documents into optimized chunks while retaining source metadata."""
        chunked_docs = self.recursive_splitter.split_documents(documents)
        
        for idx, doc in enumerate(chunked_docs):
            doc.metadata["chunk_id"] = idx
            
        return chunked_docs