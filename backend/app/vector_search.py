import json
import math
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.embeddings import create_embedding
from app.models import DocumentChunk


DEFAULT_TOP_K = 8

MIN_SIMILARITY_SCORE = 0.05

STRONG_SIMILARITY_SCORE = 0.25


def cosine_similarity(
    vector_a: List[float],
    vector_b: List[float],
) -> float:
    """
    Calculates cosine similarity between
    two vectors.
    """

    if not vector_a or not vector_b:
        return 0.0

    if len(vector_a) != len(vector_b):
        return 0.0

    try:
        dot_product = sum(
            a * b
            for a, b in zip(
                vector_a,
                vector_b,
            )
        )

        magnitude_a = math.sqrt(
            sum(
                a * a
                for a in vector_a
            )
        )

        magnitude_b = math.sqrt(
            sum(
                b * b
                for b in vector_b
            )
        )

        if (
            magnitude_a == 0
            or magnitude_b == 0
        ):
            return 0.0

        similarity = (
            dot_product
            / (
                magnitude_a
                * magnitude_b
            )
        )

        return max(
            -1.0,
            min(
                1.0,
                similarity,
            ),
        )

    except (
        TypeError,
        ValueError,
        OverflowError,
        ZeroDivisionError,
    ):
        return 0.0


def serialize_embedding(
    embedding: List[float],
) -> str:
    """
    Converts an embedding vector into JSON
    so it can be stored in SQLite.
    """

    if not embedding:
        raise ValueError(
            "Cannot serialize an empty embedding."
        )

    return json.dumps(
        embedding,
        separators=(",", ":"),
    )


def deserialize_embedding(
    embedding_json: Optional[str],
) -> Optional[List[float]]:
    """
    Converts a stored JSON embedding back
    into a list of floats.
    """

    if not embedding_json:
        return None

    try:
        parsed = json.loads(
            embedding_json
        )

        if not isinstance(
            parsed,
            list,
        ):
            return None

        if not parsed:
            return None

        cleaned_embedding: List[float] = []

        for value in parsed:
            if isinstance(
                value,
                bool,
            ):
                return None

            cleaned_embedding.append(
                float(value)
            )

        return cleaned_embedding

    except (
        json.JSONDecodeError,
        TypeError,
        ValueError,
        OverflowError,
    ):
        return None


def search_similar_chunks(
    db: Session,
    query: str,
    document_ids: Optional[List[int]] = None,
    top_k: int = DEFAULT_TOP_K,
    min_score: float = MIN_SIMILARITY_SCORE,
) -> List[Dict[str, Any]]:
    """
    Searches document chunks using cosine similarity.

    IMPORTANT:
    The returned objects intentionally contain flat fields.

    Example:

        {
            "chunk_id": 1,
            "document_id": 5,
            "filename": "sample.pdf",
            "chunk_index": 0,
            "page_number": 1,
            "score": 0.82,
            "content": "..."
        }

    chat.py must use these fields directly.
    """

    cleaned_query = (
        query.strip()
        if isinstance(
            query,
            str,
        )
        else ""
    )

    if not cleaned_query:
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty.",
        )

    if top_k <= 0:
        raise HTTPException(
            status_code=400,
            detail="top_k must be greater than zero.",
        )

    top_k = min(
        int(top_k),
        20,
    )

    if not -1.0 <= min_score <= 1.0:
        raise HTTPException(
            status_code=400,
            detail=(
                "min_score must be between "
                "-1.0 and 1.0."
            ),
        )

    cleaned_document_ids = None

    if document_ids:
        try:
            cleaned_document_ids = list(
                dict.fromkeys(
                    int(document_id)
                    for document_id in document_ids
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid document ID.",
            )

    # ---------------------------------------------------------
    # Create query embedding
    # ---------------------------------------------------------

    try:
        query_embedding = create_embedding(
            cleaned_query
        )

    except HTTPException:
        raise

    except Exception as error:
        print("=" * 70)
        print("QUERY EMBEDDING ERROR")
        print("=" * 70)

        print(
            "Error type:",
            type(error).__name__,
        )

        print(
            "Error:",
            str(error),
        )

        print("=" * 70)

        raise HTTPException(
            status_code=500,
            detail=(
                "The AI search service could not "
                "process your question."
            ),
        )

    if not query_embedding:
        raise HTTPException(
            status_code=500,
            detail=(
                "The AI search service returned "
                "an empty search embedding."
            ),
        )

    # ---------------------------------------------------------
    # Find stored document chunks
    # ---------------------------------------------------------

    query_builder = (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.embedding.isnot(None)
        )
    )

    if cleaned_document_ids:
        query_builder = query_builder.filter(
            DocumentChunk.document_id.in_(
                cleaned_document_ids
            )
        )

    chunks = query_builder.all()

    print("=" * 70)
    print("DOCUMENT VECTOR SEARCH")
    print("=" * 70)

    print(
        "Question:",
        cleaned_query,
    )

    print(
        "Selected document IDs:",
        cleaned_document_ids,
    )

    print(
        "Embedded chunks found:",
        len(chunks),
    )

    print(
        "Query embedding dimensions:",
        len(query_embedding),
    )

    print("=" * 70)

    if not chunks:
        print(
            "WARNING: No embedded chunks were found."
        )

        return []

    # ---------------------------------------------------------
    # Calculate similarity
    # ---------------------------------------------------------

    all_results: List[
        Dict[str, Any]
    ] = []

    skipped_invalid = 0

    skipped_dimension = 0

    for chunk in chunks:

        stored_embedding = (
            deserialize_embedding(
                chunk.embedding
            )
        )

        if not stored_embedding:
            skipped_invalid += 1
            continue

        if len(stored_embedding) != len(
            query_embedding
        ):
            skipped_dimension += 1

            print(
                "Skipping chunk",
                chunk.id,
                "- embedding dimension mismatch.",
                "Stored:",
                len(stored_embedding),
                "Query:",
                len(query_embedding),
            )

            continue

        score = cosine_similarity(
            query_embedding,
            stored_embedding,
        )

        document = chunk.document

        if not document:
            continue

        all_results.append(
            {
                "chunk_id": chunk.id,

                "document_id": chunk.document_id,

                "filename": document.filename,

                "chunk_index": chunk.chunk_index,

                "page_number": chunk.page_number,

                "score": round(
                    float(score),
                    6,
                ),

                "content": chunk.content,
            }
        )

    # ---------------------------------------------------------
    # No valid results
    # ---------------------------------------------------------

    if not all_results:
        print("=" * 70)
        print("NO VALID VECTOR SEARCH RESULTS")
        print("=" * 70)

        print(
            "Invalid embeddings:",
            skipped_invalid,
        )

        print(
            "Dimension mismatches:",
            skipped_dimension,
        )

        print("=" * 70)

        return []

    # ---------------------------------------------------------
    # Sort by similarity
    # ---------------------------------------------------------

    all_results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    print("=" * 70)
    print("TOP VECTOR SEARCH RESULTS")
    print("=" * 70)

    for result in all_results[:top_k]:
        print(
            f"Chunk {result['chunk_id']} | "
            f"Document {result['document_id']} | "
            f"Score {result['score']:.4f} | "
            f"Page {result.get('page_number')}"
        )

    print("=" * 70)

    # ---------------------------------------------------------
    # Apply minimum similarity
    # ---------------------------------------------------------

    filtered_results = [
        result
        for result in all_results
        if result["score"] >= min_score
    ]

    if filtered_results:
        print(
            "Returning results above minimum score:",
            len(filtered_results[:top_k]),
        )

        return filtered_results[:top_k]

    # ---------------------------------------------------------
    # Fallback
    #
    # We still return the best available chunks.
    # This is useful for small document collections.
    # ---------------------------------------------------------

    print(
        "No results reached the minimum similarity score."
    )

    print(
        "Returning best available chunks instead."
    )

    return all_results[:top_k]


def search_documents(
    db: Session,
    query: str,
    document_ids: Optional[List[int]] = None,
    top_k: int = DEFAULT_TOP_K,
    min_score: float = MIN_SIMILARITY_SCORE,
) -> List[Dict[str, Any]]:
    """
    Main document search function used by chat.py.
    """

    return search_similar_chunks(
        db=db,
        query=query,
        document_ids=document_ids,
        top_k=top_k,
        min_score=min_score,
    )


def build_rag_context(
    chunks: List[Dict[str, Any]],
) -> str:
    """
    Converts vector search results into
    readable RAG context.
    """

    if not chunks:
        return (
            "No relevant document context was found."
        )

    context_blocks = []

    for index, chunk in enumerate(
        chunks,
        start=1,
    ):
        filename = str(
            chunk.get(
                "filename",
                "Unknown document",
            )
        )

        page_number = chunk.get(
            "page_number"
        )

        score = chunk.get(
            "score",
            0,
        )

        content = str(
            chunk.get(
                "content",
                "",
            )
        ).strip()

        if not content:
            continue

        if page_number is not None:
            page_label = (
                f"Page {page_number}"
            )
        else:
            page_label = (
                "Page number unavailable"
            )

        context_blocks.append(
            "\n".join(
                [
                    f"--- SOURCE {index} ---",
                    f"Document: {filename}",
                    f"Page: {page_label}",
                    f"Similarity: {float(score):.4f}",
                    "Content:",
                    content,
                    f"--- END SOURCE {index} ---",
                ]
            )
        )

    if not context_blocks:
        return (
            "No usable document context was found."
        )

    return "\n\n".join(
        context_blocks
    )


def format_source_references(
    chunks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Creates clean source information for the frontend.
    """

    if not chunks:
        return []

    sources: List[
        Dict[str, Any]
    ] = []

    seen = set()

    for chunk in chunks:

        document_id = chunk.get(
            "document_id"
        )

        page_number = chunk.get(
            "page_number"
        )

        filename = chunk.get(
            "filename",
            "Unknown document",
        )

        chunk_index = chunk.get(
            "chunk_index",
            0,
        )

        score = chunk.get(
            "score",
            0.0,
        )

        duplicate_key = (
            document_id,
            page_number,
        )

        if duplicate_key in seen:
            continue

        seen.add(
            duplicate_key
        )

        try:
            clean_score = float(
                score
            )

        except (
            TypeError,
            ValueError,
        ):
            clean_score = 0.0

        sources.append(
            {
                "document_id": document_id,
                "filename": str(
                    filename
                ),
                "page_number": page_number,
                "chunk_index": chunk_index,
                "score": round(
                    clean_score,
                    6,
                ),
            }
        )

    return sources


def get_best_source(
    chunks: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Returns the highest-scoring result.
    """

    if not chunks:
        return None

    sorted_chunks = sorted(
        chunks,
        key=lambda item: float(
            item.get(
                "score",
                0.0,
            )
        ),
        reverse=True,
    )

    return sorted_chunks[0]


def get_search_summary(
    chunks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Provides summary information about
    the vector search results.
    """

    if not chunks:
        return {
            "result_count": 0,
            "document_count": 0,
            "best_score": 0.0,
            "strong_match": False,
            "sources": [],
        }

    document_ids = {
        chunk.get("document_id")
        for chunk in chunks
        if chunk.get("document_id") is not None
    }

    scores = []

    for chunk in chunks:
        try:
            scores.append(
                float(
                    chunk.get(
                        "score",
                        0.0,
                    )
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

    best_score = (
        max(scores)
        if scores
        else 0.0
    )

    return {
        "result_count": len(chunks),

        "document_count": len(
            document_ids
        ),

        "best_score": round(
            best_score,
            6,
        ),

        "strong_match": (
            best_score
            >= STRONG_SIMILARITY_SCORE
        ),

        "sources": format_source_references(
            chunks
        ),
    }