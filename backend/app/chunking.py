from typing import Any, Dict, List


DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 200


def normalize_text(text: str) -> str:
    """
    Cleans extracted document text.

    Removes unnecessary blank lines and
    trims whitespace from every line.
    """

    if not text:
        return ""

    lines = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        lines.append(line)

    return "\n".join(lines).strip()


def split_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[str]:
    """
    Splits text into overlapping chunks.

    Example:
        chunk_size = 1200
        overlap = 200

    Each new chunk starts 200 characters
    before the previous chunk ended.
    """

    text = normalize_text(text)

    if not text:
        return []

    if chunk_size <= 0:
        raise ValueError(
            "chunk_size must be greater than 0."
        )

    if overlap < 0:
        raise ValueError(
            "overlap cannot be negative."
        )

    if overlap >= chunk_size:
        raise ValueError(
            "overlap must be smaller than chunk_size."
        )

    chunks: List[str] = []

    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(
            start + chunk_size,
            text_length,
        )

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        start = end - overlap

    return chunks


def create_page_chunks(
    pages: List[Dict[str, Any]],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[Dict[str, Any]]:
    """
    Creates chunks while keeping the original
    page number attached to every chunk.
    """

    all_chunks: List[Dict[str, Any]] = []

    chunk_index = 0

    for page in pages:
        page_number = page.get(
            "page_number"
        )

        page_text = page.get(
            "text",
            "",
        )

        page_text = normalize_text(
            page_text
        )

        if not page_text:
            continue

        page_chunks = split_text(
            page_text,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        for chunk in page_chunks:
            all_chunks.append(
                {
                    "chunk_index": chunk_index,
                    "content": chunk,
                    "page_number": page_number,
                }
            )

            chunk_index += 1

    return all_chunks