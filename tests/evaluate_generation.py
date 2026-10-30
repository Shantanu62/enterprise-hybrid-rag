
import json

from tests.generation_evaluation_dataset import (
    GENERATION_EVALUATION_DATASET,
)
from retrieval.rag_service import RAGService


def evaluate_answer(rag, question, expected_facts, answerable):
    result = rag.answer(question)
    answer = result["answer"]

    if not answerable:
        passed = (
            len(result["sources"]) == 0
            and "not provide enough" in answer.lower()
        )

        return {
            "faithfulness": None,
            "answer_relevance": None,
            "fact_results": [],
            "abstention_pass": passed,
            "answer": answer,
            "reason": "",
        }

    if not expected_facts:
        raise ValueError(
            f"Answerable question has no expected facts: {question}"
        )

    # Retrieve and rerank documents to reconstruct the context.
    results = rag.search_service.search(question, limit=5)
    ranked_results = rag.rerank_results(question, results)

    relevant_results = [
        item for item in ranked_results
        if item["reranker_score"] > 0.0
    ][:rag.final_source_limit]

    context = "\n\n".join(
        item.get("text", "")
        for item in relevant_results
    )

    judge_prompt = f"""
You are an independent and strict evaluator of a
Retrieval-Augmented Generation (RAG) system.

Evaluate the generated answer using ONLY the supplied context.

QUESTION:
{question}

CONTEXT:
{context}

EXPECTED FACTS:
{json.dumps(expected_facts, ensure_ascii=False)}

GENERATED ANSWER:
{answer}

Evaluate these three metrics:

1. faithfulness:
Score from 0 to 1.
1 means every factual claim in the answer is supported by the context.
0 means the answer contains unsupported factual claims.

2. answer_relevance:
Score from 0 to 1.
1 means the answer directly and completely addresses the question.
0 means the answer is unrelated or does not answer the question.

3. fact_results:
Evaluate EVERY expected fact individually.

For each expected fact:
- Set "covered" to true only if the generated answer clearly
  communicates that fact.
- Paraphrasing is allowed.
- The fact must also be supported by the supplied context.
- Set "covered" to false if the fact is missing, incomplete,
  contradicted, or unsupported.
- Do not assume that a fact is covered merely because it appears
  in the expected facts.

For conflicting information, give credit when the answer
accurately explains the conflict.

Return ONLY valid JSON in this exact structure:
{{
    "faithfulness": 0.0,
    "answer_relevance": 0.0,
    "fact_results": [
        {{
            "fact": "Expected fact text",
            "covered": true
        }}
    ],
    "reason": "Brief explanation"
}}

IMPORTANT:
- Include exactly one fact_results entry for every expected fact.
- Do not skip any expected fact.
- Use true or false for covered, not strings.
"""

    response = rag.client.chat.completions.create(
        model=rag.model_name,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict, objective and evidence-based "
                    "RAG evaluator. Follow the requested JSON structure."
                ),
            },
            {
                "role": "user",
                "content": judge_prompt,
            },
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    evaluation = json.loads(
        response.choices[0].message.content
    )

    fact_results = evaluation["fact_results"]

    if len(fact_results) != len(expected_facts):
        raise ValueError(
            f"Expected {len(expected_facts)} fact results, "
            f"but received {len(fact_results)} for: {question}"
        )

    # Validate the judge's fact-level response.
    for expected, actual in zip(expected_facts, fact_results):
        if actual["fact"] != expected:
            raise ValueError(
                f"Fact mismatch for question: {question}"
            )

        if not isinstance(actual["covered"], bool):
            raise ValueError(
                f"Invalid covered value for fact: {expected}"
            )

    return {
        "faithfulness": float(evaluation["faithfulness"]),
        "answer_relevance": float(evaluation["answer_relevance"]),
        "fact_results": fact_results,
        "reason": evaluation.get("reason", ""),
        "abstention_pass": None,
        "answer": answer,
    }


def main():
    rag = RAGService()

    faithfulness_total = 0.0
    relevance_total = 0.0
    evaluated_count = 0

    facts_covered_total = 0
    expected_facts_total = 0

    abstention_pass = 0
    abstention_total = 0

    try:
        print("\nRAG GENERATION EVALUATION")
        print("=" * 70)

        for item in GENERATION_EVALUATION_DATASET:
            question = item["question"]
            expected_facts = item["expected_facts"]

            print("\nQUESTION:", question)

            result = evaluate_answer(
                rag,
                question,
                expected_facts,
                item["answerable"],
            )

            print("\nGENERATED ANSWER:")
            print(result["answer"])

            if not item["answerable"]:
                abstention_total += 1

                if result["abstention_pass"]:
                    abstention_pass += 1

                print(
                    "\nABSTENTION:",
                    "PASS" if result["abstention_pass"] else "FAIL",
                )
                continue

            faithfulness = result["faithfulness"]
            relevance = result["answer_relevance"]

            faithfulness_total += faithfulness
            relevance_total += relevance
            evaluated_count += 1

            print(f"\nFaithfulness: {faithfulness:.2f}")
            print(f"Answer Relevance: {relevance:.2f}")

            # Expected Facts Coverage
            covered_count = sum(
                1 for fact in result["fact_results"]
                if fact["covered"]
            )

            total_facts = len(result["fact_results"])

            facts_covered_total += covered_count
            expected_facts_total += total_facts

            coverage = covered_count / total_facts

            print(
                f"Expected Facts Coverage: "
                f"{covered_count}/{total_facts} "
                f"({coverage * 100:.2f}%)"
            )

            print("\nFACT-LEVEL RESULTS:")

            for fact_result in result["fact_results"]:
                status = (
                    "COVERED"
                    if fact_result["covered"]
                    else "MISSING"
                )

                print(f"[{status}] {fact_result['fact']}")

            print("\nEvaluator Reason:", result["reason"])

        print("\n" + "=" * 70)
        print("OVERALL GENERATION METRICS")
        print("=" * 70)

        if evaluated_count:
            print(
                "Average Faithfulness:",
                round(faithfulness_total / evaluated_count, 4),
            )

            print(
                "Average Answer Relevance:",
                round(relevance_total / evaluated_count, 4),
            )

        if expected_facts_total:
            overall_coverage = (
                facts_covered_total / expected_facts_total
            )

            print(
                "Expected Facts Coverage:",
                f"{facts_covered_total}/{expected_facts_total}",
                f"({overall_coverage * 100:.2f}%)",
            )

        print(
            f"No-answer handling: {abstention_pass}/{abstention_total}"
        )

    finally:
        rag.close()


if __name__ == "__main__":
    main()
