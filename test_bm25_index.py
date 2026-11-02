
from core.vector_store import VectorStore
from retrieval.bm25_index import BM25IndexManager


def main():
    vector_store = VectorStore()

    try:
        manager = BM25IndexManager(vector_store)
        manager.ensure_ready()

        documents = manager.get_documents()

        print("BM25 index initialized successfully!")
        print("Documents indexed:", len(documents))
        print("BM25 metrics:", manager.last_metrics)

        results = manager.search(
            query="annual leave policy",
            limit=5,
        )

        print("\nSearch results:")

        for point_id, score in results:
            document = documents[point_id]

            print("ID:", point_id)
            print("Score:", round(score, 4))
            print("Text:", document["text"][:150])
            print("-" * 50)

    finally:
        vector_store.close()


if __name__ == "__main__":
    main()
