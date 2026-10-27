from typing import List

from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from rank_bm25 import BM25Okapi

from app.config import settings


class HybridRetrievalEngine:
    def __init__(self, documents: List[Document], collection_name: str = "enterprise_rag"):
        self.documents = documents
        self.collection_name = collection_name

        # Embedding model (local, free)
        self.embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)

        # Dense index: local in-memory Qdrant (no server / Docker needed)
        self.vector_store = QdrantVectorStore.from_documents(
            documents=self.documents,
            embedding=self.embeddings,
            location=":memory:",
            collection_name=self.collection_name,
        )

        # Sparse index: BM25 keyword search
        self.tokenized_corpus = [self._tokenize(doc.page_content) for doc in self.documents]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return text.lower().split()

    def dense_search(self, query: str, top_k: int = 5) -> List[Document]:
        """Semantic (vector) search."""
        return self.vector_store.similarity_search(query, k=top_k)

    def sparse_search(self, query: str, top_k: int = 5) -> List[Document]:
        """Keyword (BM25) search."""
        if not self.documents:
            return []
        scores = self.bm25.get_scores(self._tokenize(query))
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return [self.documents[i] for i in ranked_indices[:top_k]]

    def reciprocal_rank_fusion(
        self,
        dense_docs: List[Document],
        sparse_docs: List[Document],
        k: int = 60,
    ) -> List[Document]:
        """Merge two ranked lists using Reciprocal Rank Fusion."""
        scores = {}
        doc_map = {}

        for ranked_list in (dense_docs, sparse_docs):
            for rank, doc in enumerate(ranked_list):
                key = doc.metadata.get("chunk_id") or doc.page_content
                doc_map[key] = doc
                scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)

        sorted_keys = sorted(scores, key=scores.get, reverse=True)
        return [doc_map[key] for key in sorted_keys]