import os
from fastembed import TextEmbedding

class HybridSearchEngine:
    def __init__(self, qdrant_client):
        self.client = qdrant_client
        # FastEmbed uses minimal RAM (~100MB) compared to PyTorch (~600MB+)
        self.embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

    def get_embeddings(self, text: str):
        # FastEmbed returns a generator of numpy arrays
        embeddings = list(self.embedding_model.embed([text]))
        return embeddings[0].tolist()

    def search(self, query: str, top_k: int = 5):
        query_vector = self.get_embeddings(query)
        
        # Qdrant vector search query
        search_results = self.client.search(
            collection_name="enterprise_docs",
            query_vector=query_vector,
            limit=top_k
        )
        return search_results