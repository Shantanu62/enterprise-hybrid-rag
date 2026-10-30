
from retrieval.rag_service import RAGService


def main():
    rag = RAGService()

    questions = [
        "How should sensitive customer data be protected?",
        "How many days of annual leave do full-time employees receive?",
        "How do employees submit an IT support request?",
    ]

    try:
        for question in questions:
            print("\n" + "=" * 70)
            print("QUESTION:", question)

            results = rag.search_service.search(
                question,
                limit=5,
            )

            ranked_results = rag.rerank_results(
                question,
                results,
            )

            print("\nRERANKED DOCUMENT SCORES:")

            for result in ranked_results:
                source = result.get("metadata", {}).get(
                    "source",
                    "unknown",
                )
                score = result.get("reranker_score", 0.0)

                print(f"{source} | score: {score:.4f}")

    finally:
        rag.close()


if __name__ == "__main__":
    main()
