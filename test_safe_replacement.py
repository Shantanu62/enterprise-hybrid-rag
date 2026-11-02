
from pathlib import Path
import tempfile

from retrieval.rag_service import RAGService
from ingestion.pipeline import IngestionPipeline


TEST_FILENAME = "safe_replacement_test_unique.txt"


def main():
    rag = RAGService()
    pipeline = None

    try:
        manager = rag.search_service.bm25_index_manager

        pipeline = IngestionPipeline(
            bm25_index_manager=manager
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / TEST_FILENAME

            print("\n========== FIRST INGESTION ==========")

            test_file.write_text(
                "SAFEVERSIONONE This is the original document version.",
                encoding="utf-8",
            )

            first_result = pipeline.ingest_file(str(test_file))
            print("First result:", first_result)

            print("\n========== SECOND INGESTION ==========")

            test_file.write_text(
                "SAFEVERSIONTWO This is the updated document version.",
                encoding="utf-8",
            )

            second_result = pipeline.ingest_file(str(test_file))
            print("Second result:", second_result)

            print("\n========== CACHE VALIDATION ==========")

            print("Cache dirty:", manager._dirty)

            # Searching rebuilds the invalidated BM25 index.
            results = manager.search(
                query="SAFEVERSIONTWO",
                limit=10,
            )

            indexed_documents = manager.get_documents()

            matching_texts = [
                indexed_documents[point_id]["text"]
                for point_id, score in results
                if point_id in indexed_documents
            ]

            print("Matching results:", len(matching_texts))

            for text in matching_texts:
                print("Found:", text)

            first_version_found = any(
                "SAFEVERSIONONE" in document["text"]
                for document in indexed_documents.values()
            )

            second_version_found = any(
                "SAFEVERSIONTWO" in document["text"]
                for document in indexed_documents.values()
            )

            print("\n========== TEST SUMMARY ==========")

            print("First ingestion:", first_result["status"])
            print("Second ingestion:", second_result["status"])
            print("Old version found:", first_version_found)
            print("New version found:", second_version_found)

            if (
                first_result["status"] == "success"
                and second_result["status"] == "success"
                and not first_version_found
                and second_version_found
            ):
                print("\nPASS: Safe document replacement verified.")
            else:
                print("\nFAIL: Safe replacement needs investigation.")

    finally:
        if pipeline is not None:
            pipeline.close()

        try:
            rag.search_service.vector_store.delete_document(
                TEST_FILENAME
            )
            manager = rag.search_service.bm25_index_manager
            manager.invalidate()
            print("\nTest cleanup completed.")

        except Exception as exc:
            print("\nCleanup warning:", type(exc).__name__)

        rag.close()


if __name__ == "__main__":
    main()
