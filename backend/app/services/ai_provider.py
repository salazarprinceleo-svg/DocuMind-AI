import os

from dotenv import load_dotenv
from ollama import Client


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


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

client = Client(
    host=OLLAMA_HOST
)


# ============================================================
# STARTUP INFORMATION
# ============================================================

print("=" * 70)
print("OLLAMA AI PROVIDER INITIALIZED")
print("=" * 70)
print(
    f"Ollama host: {OLLAMA_HOST}"
)
print(
    f"Ollama model: {OLLAMA_MODEL}"
)
print("=" * 70)


# ============================================================
# MAIN OLLAMA RESPONSE FUNCTION
# ============================================================

def generate_response(
    prompt: str,
    temperature: float = 0.2,
) -> str:
    """
    Generate an AI response using the locally
    installed Ollama model.
    """

    if not prompt or not prompt.strip():
        raise ValueError(
            "Prompt cannot be empty."
        )

    try:

        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            options={
                "temperature": temperature,
            },
        )

        message = response.get(
            "message",
            {},
        )

        content = message.get(
            "content",
            "",
        )

        if not content:
            raise RuntimeError(
                "Ollama returned an empty response."
            )

        return content.strip()

    except Exception as exc:

        print("=" * 70)
        print("OLLAMA GENERATION ERROR")
        print("=" * 70)
        print(
            "Error type:",
            type(exc).__name__,
        )
        print(
            "Error:",
            str(exc),
        )
        print("=" * 70)

        raise RuntimeError(
            "Unable to generate a response using "
            f"Ollama: {exc}"
        ) from exc


# ============================================================
# COMPATIBILITY FUNCTION FOR AI TOOLS
# ============================================================

def generate_ollama_response(
    prompt: str,
    temperature: float = 0.2,
) -> str:
    """
    Compatibility wrapper for existing AI tools.

    ai_tools.py currently imports:
        generate_ollama_response

    The actual generation is handled by:
        generate_response
    """

    return generate_response(
        prompt=prompt,
        temperature=temperature,
    )