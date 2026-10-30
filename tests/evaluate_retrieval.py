
from tests.evaluation_dataset import EVALUATION_DATASET
from retrieval.hybrid_search import HybridSearchService


def calculate_precision_at_k(retrieved, relevant, k):
    if k <= 0:
        raise ValueError("k must be greater than 0.")

    retrieved_at_k = retrieved[:k]

    if not retrieved_at_k:
        return 0.0

    relevant_count = sum(
        1 for source in retrieved_at_k
        if source in relevant
    )

    return relevant_count / k


def calculate_recall_at_k(retrieved, relevant, k):
    if k <= 0:
        raise ValueError("k must be greater than 0.")

    if not relevant:
        return 0.0

    retrieved_at_k = retrieved[:k]

    relevant_count = sum(
        1 for source in retrieved_at_k
        if source in relevant
    )

    return relevant_count / len(relevant)


def calculate_mrr(retrieved, relevant):
    if not relevant:
        return 0.0

    for rank, source in enumerate(retrieved, start=1):
        if source in relevant:
            return 1 / rank

    return 0.0


def main():
    search_service = HybridSearchService()

    total_precision = 0.0
    total_recall = 0.0
    total_mrr = 0.0

    k = 3

    try:
        print("\nRAG RETRIEVAL EVALUATION")
        print("=" * 70)

        for item in EVALUATION_DATASET:
            question = item["question"]
            relevant_sources = item["relevant_sources"]

            results = search_service.search(
                question,
                limit=5,
            )

            retrieved_sources = [
                result["metadata"].get("source", "unknown")
                for result in results
            ]

            precision = calculate_precision_at_k(
                retrieved_sources,
                relevant_sources,
                k,
            )

            recall = calculate_recall_at_k(
                retrieved_sources,
                relevant_sources,
                k,
            )

            mrr = calculate_mrr(
                retrieved_sources,
                relevant_sources,
            )

            total_precision += precision
            total_recall += recall
            total_mrr += mrr

            print("\nQUESTION:", question)
            print("EXPECTED:", relevant_sources)
            print("RETRIEVED:", retrieved_sources)
            print(f"Precision@{k}: {precision:.4f}")
            print(f"Recall@{k}: {recall:.4f}")
            print(f"MRR: {mrr:.4f}")

        total = len(EVALUATION_DATASET)

        print("\n" + "=" * 70)
        print("OVERALL METRICS")
        print("=" * 70)
        print(f"Average Precision@{k}: {total_precision / total:.4f}")
        print(f"Average Recall@{k}: {total_recall / total:.4f}")
        print(f"Mean Reciprocal Rank: {total_mrr / total:.4f}")

    finally:
        search_service.close()


if __name__ == "__main__":
    main()
