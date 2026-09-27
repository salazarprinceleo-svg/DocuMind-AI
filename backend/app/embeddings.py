import os
from typing import Any, List

from dotenv import load_dotenv
from fastapi import HTTPException
from ollama import Client


load_dotenv()


OLLAMA_HOST = os.getenv(
    "OLLAMA_HOST",
    "http://127.0.0.1:11434",
)

OLLAMA_EMBEDDING_MODEL = os.getenv(
    "OLLAMA_EMBEDDING_MODEL",
    "nomic-embed-text",
)


client = None


try:
    client = Client(
        host=OLLAMA_HOST
    )

    print("=" * 70)
    print("OLLAMA EMBEDDING PROVIDER INITIALIZED")
    print("=" * 70)

    print(
        "Ollama host:",
        OLLAMA_HOST,
    )

    print(
        "Embedding model:",
        OLLAMA_EMBEDDING_MODEL,
    )

    print("=" * 70)

except Exception as error:
    print("=" * 70)
    print("OLLAMA EMBEDDING INITIALIZATION ERROR")
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

    client = None


def check_embedding_client() -> None:
    """
    Makes sure the local Ollama client exists.
    """

    if client is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Local Ollama embeddings are not available. "
                "Please make sure Ollama is installed and "
                "running on your computer."
            ),
        )


def _extract_embeddings_from_response(
    response: Any,
) -> List[float]:
    """
    Handles both dictionary-style and object-style
    responses from different Ollama Python client versions.
    """

    embeddings = None

    # Dictionary-style response
    if isinstance(response, dict):
        embeddings = response.get(
            "embeddings"
        )

    # Object-style response
    if embeddings is None:
        embeddings = getattr(
            response,
            "embeddings",
            None,
        )

    if not embeddings:
        raise ValueError(
            "Ollama returned no embeddings."
        )

    first_embedding = embeddings[0]

    if not first_embedding:
        raise ValueError(
            "Ollama returned an empty embedding."
        )

    return list(
        first_embedding
    )


def create_embedding(
    text: str,
) -> List[float]:
    """
    Creates a local vector embedding using
    Ollama's nomic-embed-text model.
    """

    check_embedding_client()

    if not isinstance(text, str):
        raise ValueError(
            "Embedding text must be a string."
        )

    cleaned_text = text.strip()

    if not cleaned_text:
        raise ValueError(
            "Cannot create an embedding from empty text."
        )

    try:
        print("=" * 70)
        print("CREATING OLLAMA EMBEDDING")
        print("=" * 70)

        print(
            "Model:",
            OLLAMA_EMBEDDING_MODEL,
        )

        print(
            "Text length:",
            len(cleaned_text),
        )

        print("=" * 70)

        response = client.embed(
            model=OLLAMA_EMBEDDING_MODEL,
            input=cleaned_text,
        )

        if not response:
            raise ValueError(
                "Ollama returned no response."
            )

        embedding = (
            _extract_embeddings_from_response(
                response
            )
        )

        print(
            "Embedding dimensions:",
            len(embedding),
        )

        print(
            "OLLAMA EMBEDDING SUCCESS"
        )

        print("=" * 70)

        return embedding

    except HTTPException:
        raise

    except Exception as error:
        print("=" * 70)
        print("OLLAMA EMBEDDING ERROR")
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
            status_code=503,
            detail=(
                "The local Ollama embedding service "
                "could not create an embedding. "
                "Make sure Ollama is running and the "
                "nomic-embed-text model is installed."
            ),
        )