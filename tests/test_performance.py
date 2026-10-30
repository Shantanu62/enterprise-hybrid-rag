
from retrieval.rag_service import RAGService


TEST_QUESTIONS = [
    "How should sensitive customer data be protected?",
    "How many days of annual leave do full-time employees receive?",
    "How do employees submit an IT support request?",
    "What is the company parental leave policy?",
    "What authentication method must employees use?",
]


def main():
    rag = RAGService()

    try:
        print("\nRAG PERFORMANCE EVALUATION")
        print("=" * 70)

        for question in TEST_QUESTIONS:

            print("\nQUESTION:", question)

            result = rag.answer(question)

            print("\nANSWER:")
            print(result["answer"])

            metrics = result["performance"]

            print("\nPERFORMANCE METRICS")
            print("-" * 50)

            for metric, value in metrics.items():
                print(f"{metric}: {value:.2f} ms")

            print("-" * 50)

    finally:
        rag.close()


if __name__ == "__main__":
    main()
