
from retrieval.rag_service import RAGService


def main():
    rag = RAGService()

    questions = [
        "How should sensitive customer data be protected?",
        "How many days of annual leave do full-time employees receive?",
        "How do employees submit an IT support request?",
        "What is the company parental leave policy?",
    ]

    try:
        for question in questions:
            print("\n" + "=" * 70)
            print("QUESTION:", question)

            result = rag.answer(question)

            print("\nANSWER:")
            print(result["answer"])

            print("\nSOURCES:")

            for source in result["sources"]:
                print(source)

    finally:
        rag.close()


if __name__ == "__main__":
    main()
