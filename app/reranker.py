from typing import List
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder

class RerankingPipeline:
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        # Initializing lightweight local cross-encoder for zero-cost reranking
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, documents: List[Document], top_k: int = 3) -> List[Document]:
        """Scores and re-orders documents using a Cross-Encoder for high contextual precision."""
        if not documents:
            return []

        pairs = [[query, doc.page_content] for doc in documents]
        scores = self.model.predict(pairs)

        # Attach scores to documents and sort
        scored_docs = list(zip(documents, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        # Return top_k reranked documents
        return [doc for doc, score in scored_docs[:top_k]]