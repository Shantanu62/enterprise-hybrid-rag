
from collections import defaultdict
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import models

from core.vector_store import VectorStore


def main() -> None:
    store = VectorStore()

    try:
        collection = store.collection_name
        offset = None
        all_points = []

        while True:
            points, next_offset = store.client.scroll(
                collection_name=collection,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            all_points.extend(points)

            if next_offset is None:
                break

            offset = next_offset

        groups = defaultdict(list)

        for point in all_points:
            payload = point.payload or {}
            text = payload.get("text", "")
            metadata = payload.get("metadata", {})

            source = metadata.get("source", "unknown")
            page = metadata.get("page", "")
            chunk_index = metadata.get("chunk_index", "")

            # Only group points with the same source, location,
            # chunk index, and exact text.
            key = (source, page, chunk_index, text)
            groups[key].append(point)

        duplicate_ids = []

        for key, group in groups.items():
            if len(group) <= 1:
                continue

            source, page, chunk_index, _ = key

            canonical_id = str(
                uuid5(
                    NAMESPACE_URL,
                    f"{source}|{page}|{chunk_index}",
                )
            )

            keep = next(
                (point for point in group if str(point.id) == canonical_id),
                group[0],
            )

            for point in group:
                if point.id != keep.id:
                    duplicate_ids.append(point.id)

        print("Total points found:", len(all_points))
        print("Duplicate points to remove:", len(duplicate_ids))

        if duplicate_ids:
            store.client.delete(
                collection_name=collection,
                points_selector=models.PointIdsList(
                    points=duplicate_ids
                ),
                wait=True,
            )
            print("Duplicate cleanup completed.")
        else:
            print("No duplicate points found.")

        remaining = store.client.count(
            collection_name=collection,
            exact=True,
        )
        print("Remaining points:", remaining.count)

    finally:
        store.close()


if __name__ == "__main__":
    main()
