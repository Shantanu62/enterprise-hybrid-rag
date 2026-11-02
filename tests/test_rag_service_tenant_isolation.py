
from unittest.mock import MagicMock

import pytest

from retrieval.rag_service import RAGService


@pytest.fixture
def service():
    instance = RAGService.__new__(RAGService)

    instance.model_name = "openai/gpt-oss-20b"
    instance.retrieval_limit = 5
    instance.final_source_limit = 3
    instance.reranker_score_threshold = 0.0

    instance.search_service = MagicMock()
    instance.search_service.last_metrics = {
        "retrieval_ms": 12.0
    }

    instance.reranker = MagicMock()
    instance.client = MagicMock()
    instance.last_metrics = {}

    return instance


def make_result(tenant_id="tenant-a"):
    return {
        "id": "point-1",
        "text": "Customer support policy",
        "metadata": {
            "tenant_id": tenant_id,
            "source": "support-policy.pdf",
            "page": 1,
        },
        "score": 0.95,
    }


def test_answer_passes_tenant_to_search(service):
    service.search_service.search.return_value = []

    result = service.answer(
        question="  What is the support policy?  ",
        tenant_id="tenant-a",
    )

    service.search_service.search.assert_called_once_with(
        query="What is the support policy?",
        tenant_id="tenant-a",
        limit=5,
    )

    assert result["tenant_id"] == "tenant-a"
    assert result["sources"] == []
    service.reranker.predict.assert_not_called()
    service.client.chat.completions.create.assert_not_called()


def test_answer_rejects_cross_tenant_results_before_reranking(service):
    service.search_service.search.return_value = [
        make_result(tenant_id="tenant-b")
    ]

    with pytest.raises(RuntimeError, match="Cross-tenant"):
        service.answer(
            question="What is the support policy?",
            tenant_id="tenant-a",
        )

    service.reranker.predict.assert_not_called()
    service.client.chat.completions.create.assert_not_called()


def test_answer_rejects_missing_metadata_before_reranking(service):
    service.search_service.search.return_value = [
        {
            "id": "point-1",
            "text": "Customer support policy",
            "metadata": None,
        }
    ]

    with pytest.raises(RuntimeError, match="Invalid document metadata"):
        service.answer(
            question="What is the support policy?",
            tenant_id="tenant-a",
        )

    service.reranker.predict.assert_not_called()


def test_answer_rejects_empty_tenant_id(service):
    with pytest.raises(ValueError, match="tenant_id"):
        service.answer(
            question="What is the support policy?",
            tenant_id="",
        )

    service.search_service.search.assert_not_called()


def test_answer_rejects_empty_question(service):
    with pytest.raises(ValueError, match="Question"):
        service.answer(
            question="   ",
            tenant_id="tenant-a",
        )

    service.search_service.search.assert_not_called()


def test_answer_generates_grounded_response(service):
    service.search_service.search.return_value = [
        make_result()
    ]

    service.reranker.predict.return_value = [0.85]

    mock_response = MagicMock()
    mock_response.choices[0].message.content = (
        "Customers can contact support for assistance."
    )

    service.client.chat.completions.create.return_value = mock_response

    result = service.answer(
        question="What is the support policy?",
        tenant_id="tenant-a",
    )

    assert result["tenant_id"] == "tenant-a"
    assert result["answer"] == (
        "Customers can contact support for assistance."
    )
    assert len(result["sources"]) == 1
    assert result["sources"][0]["source"] == "support-policy.pdf"
    assert result["model"] == "openai/gpt-oss-20b"

    service.client.chat.completions.create.assert_called_once()


def test_close_closes_search_service(service):
    service.close()

    service.search_service.close.assert_called_once()
