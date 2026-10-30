
from sentence_transformers import CrossEncoder

from tests.evaluation_dataset import EVALUATION_DATASET
from retrieval.hybrid_search import HybridSearchService


def calculate_metrics(retrieved, relevant, k=3):
    if not relevant:
        return None

    top_k = retrieved[:k]

    relevant_count = sum(
        1 for source in top_k
        if source in relevant
    )

    precision_at_k = relevant_count / k

    precision_returned = (
        relevant_count / len(top_k)
        if top_k else 0.0
    )

    recall = relevant_count / len(relevant)

    reciprocal_rank = 0.0

    for rank, source in enumerate(retrieved, start=1):
        if source in relevant:
            reciprocal_rank = 1 / rank
            break

    return (
        precision_at_k,
        precision_returned,
        recall,
        reciprocal_rank,
    )


def main():
    search_service = HybridSearchService()

    reranker = CrossEncoder(
        "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )

    threshold = 0.0
    k = 3

    totals = [0.0, 0.0, 0.0, 0.0]

    evaluated_queries = 0
    no_answer_correct = 0
    no_answer_total = 0

    try:
        print("\nCROSS-ENCODER RERANKING EVALUATION")
        print("=" * 70)

        for item in EVALUATION_DATASET:

            question = item["question"]
            relevant_sources = item["relevant_sources"]

            results = search_service.search(
                question,
                limit=5,
            )

            pairs = [
                (question, result["text"])
                for result in results
            ]

            scores = reranker.predict(pairs)

            ranked_results = []

            for result, score in zip(results, scores):
                ranked_results.append({
                    **result,
                    "reranker_score": float(score),
                })

            ranked_results.sort(
                key=lambda item: item["reranker_score"],
                reverse=True,
            )

            filtered_results = [
                result
                for result in ranked_results
                if result["reranker_score"] > threshold
            ]

            retrieved_sources = [
                result["metadata"].get("source", "unknown")
                for result in filtered_results
            ]

            print("\nQUESTION:", question)
            print("EXPECTED:", relevant_sources)
            print("FILTERED:", retrieved_sources)

            if not relevant_sources:
                no_answer_total += 1

                if not filtered_results:
                    no_answer_correct += 1

                print(
                    "NO-ANSWER DETECTION:",
                    "PASS" if not filtered_results else "FAIL",
                )
                continue

            metrics = calculate_metrics(
                retrieved_sources,
                relevant_sources,
                k,
            )

            p_at_k, p_returned, recall, mrr = metrics

            totals[0] += p_at_k
            totals[1] += p_returned
            totals[2] += recall
            totals[3] += mrr

            evaluated_queries += 1

            print(f"Precision@{k}: {p_at_k:.4f}")
            print(f"Precision@Returned: {p_returned:.4f}")
            print(f"Recall@{k}: {recall:.4f}")
            print(f"MRR: {mrr:.4f}")

        print("\n" + "=" * 70)
        print("RERANKING OVERALL METRICS")
        print("=" * 70)

        if evaluated_queries:
            print(
                f"Average Precision@{k}: "
                f"{totals[0] / evaluated_queries:.4f}"
            )
            print(
                "Average Precision@Returned: "
                f"{totals[1] / evaluated_queries:.4f}"
            )
            print(
                f"Average Recall@{k}: "
                f"{totals[2] / evaluated_queries:.4f}"
            )
            print(
                f"Mean Reciprocal Rank: "
                f"{totals[3] / evaluated_queries:.4f}"
            )

        print(
            "\nNo-answer detection accuracy: "
            f"{no_answer_correct}/{no_answer_total}"
        )

    finally:
        search_service.close()


if __name__ == "__main__":
    main()
