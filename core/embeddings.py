
from fastembed import TextEmbedding


class EmbeddingService:
    """Generate vector embeddings for document chunks and queries."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
    ) -> None:
        self.model_name = model_name
        self.model = TextEmbedding(model_name=model_name)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Convert multiple texts into embedding vectors."""

        if not texts:
            return []

        if not all(isinstance(text, str) and text.strip() for text in texts):
            raise ValueError("Every text must be a non-empty string.")

        vectors = self.model.embed(texts)

        return [vector.tolist() for vector in vectors]

    def embed_query(self, query: str) -> list[float]:
        """Convert a user query into a single embedding vector."""

        if not isinstance(query, str) or not query.strip():
            raise ValueError("Query must be a non-empty string.")

        # BGE models use a query instruction for retrieval.
        prepared_query = f"Represent this sentence for searching relevant passages: {query.strip()}"

        return self.embed_texts([prepared_query])[0]
