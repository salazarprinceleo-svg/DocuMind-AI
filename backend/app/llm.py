import os
from typing import Any

from dotenv import load_dotenv
from fastapi import HTTPException
from ollama import Client


load_dotenv()


# ============================================================
# OLLAMA CONFIGURATION
# ============================================================

OLLAMA_HOST = os.getenv(
    "OLLAMA_HOST",
    "http://127.0.0.1:11434",
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "gemma3:1b",
)


# ============================================================
# OLLAMA CLIENT
# ============================================================

client = None


try:
    client = Client(
        host=OLLAMA_HOST
    )

    print("=" * 70)
    print("OLLAMA LOCAL AI PROVIDER INITIALIZED")
    print("=" * 70)

    print(
        "Ollama host:",
        OLLAMA_HOST,
    )

    print(
        "AI model:",
        OLLAMA_MODEL,
    )

    print("=" * 70)

except Exception as error:

    print("=" * 70)
    print("OLLAMA AI INITIALIZATION ERROR")
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


# ============================================================
# CHECK OLLAMA
# ============================================================


def check_llm_client() -> None:
    """
    Makes sure the Ollama client is available.
    """

    if client is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Local Ollama AI is not available. "
                "Please make sure Ollama is installed "
                "and running on your computer."
            ),
        )


# ============================================================
# GENERATE RESPONSE
# ============================================================


def generate_response(
    prompt: str,
) -> str:
    """
    Generates an AI response using the local
    Ollama model.
    """

    check_llm_client()

    if not isinstance(
        prompt,
        str,
    ):
        raise ValueError(
            "Prompt must be a string."
        )

    cleaned_prompt = prompt.strip()

    if not cleaned_prompt:
        raise ValueError(
            "Prompt cannot be empty."
        )

    try:

        print("=" * 70)
        print("OLLAMA AI REQUEST")
        print("=" * 70)

        print(
            "Model:",
            OLLAMA_MODEL,
        )

        print(
            "Prompt length:",
            len(cleaned_prompt),
        )

        print("=" * 70)

        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": cleaned_prompt,
                }
            ],
        )

        if not response:
            raise ValueError(
                "Ollama returned no response."
            )

        # ----------------------------------------------------
        # Dictionary response
        # ----------------------------------------------------

        if isinstance(
            response,
            dict,
        ):

            message = response.get(
                "message"
            )

            if isinstance(
                message,
                dict,
            ):

                content = message.get(
                    "content"
                )

                if content:

                    print("=" * 70)
                    print(
                        "OLLAMA AI RESPONSE SUCCESS"
                    )
                    print("=" * 70)

                    return str(
                        content
                    ).strip()

            # Some Ollama responses may expose
            # content directly.

            content = response.get(
                "content"
            )

            if content:

                print("=" * 70)
                print(
                    "OLLAMA AI RESPONSE SUCCESS"
                )
                print("=" * 70)

                return str(
                    content
                ).strip()

        # ----------------------------------------------------
        # Object response
        # ----------------------------------------------------

        message = getattr(
            response,
            "message",
            None,
        )

        if message is not None:

            content = getattr(
                message,
                "content",
                None,
            )

            if content:

                print("=" * 70)
                print(
                    "OLLAMA AI RESPONSE SUCCESS"
                )
                print("=" * 70)

                return str(
                    content
                ).strip()

        # ----------------------------------------------------
        # Direct content
        # ----------------------------------------------------

        content = getattr(
            response,
            "content",
            None,
        )

        if content:

            print("=" * 70)
            print(
                "OLLAMA AI RESPONSE SUCCESS"
            )
            print("=" * 70)

            return str(
                content
            ).strip()

        # ----------------------------------------------------
        # Nothing usable
        # ----------------------------------------------------

        raise ValueError(
            "Ollama returned a response, "
            "but no text content could be extracted."
        )

    except HTTPException:
        raise

    except Exception as error:

        print("=" * 70)
        print("OLLAMA AI GENERATION ERROR")
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
                "The local Ollama AI service could not "
                "generate a response. Make sure Ollama "
                "is running and the configured model "
                f"'{OLLAMA_MODEL}' is installed."
            ),
        )