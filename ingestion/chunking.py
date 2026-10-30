
from typing import Any


def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[str]:
    """Split text into chunks while preserving word boundaries."""

    if not isinstance(text, str):
        raise TypeError("text must be a string.")

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0.")

    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError(
            "chunk_overlap must be >= 0 and smaller than chunk_size."
        )

    text = text.strip()

    if not text:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)

        if end < text_length:
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        next_start = end - chunk_overlap

        # Move forward to the next word boundary.
        while next_start < end and text[next_start] != " ":
            next_start += 1

        start = next_start + 1

    return chunks


def chunk_documents(
    records: list[dict[str, Any]],
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[dict[str, Any]]:
    """Chunk loaded documents and preserve source metadata."""

    chunked_records = []

    for record in records:
        chunks = chunk_text(
            text=record.get("text", ""),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        for index, chunk in enumerate(chunks, start=1):
            chunked_records.append(
                {
                    "text": chunk,
                    "metadata": {
                        **record.get("metadata", {}),
                        "chunk_index": index,
                    },
                }
            )

    return chunked_records
