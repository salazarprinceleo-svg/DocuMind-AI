import json
import re

from typing import Any

from dotenv import load_dotenv

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from app.database import get_db

from app.models import Document

from app.services.ai_provider import (
    generate_ollama_response,
)


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/api/ai",
    tags=["AI Learning Tools"],
)


# ============================================================
# REQUEST MODELS
# ============================================================

class FlashcardRequest(BaseModel):

    count: int = Field(
        default=10,
        ge=3,
        le=30,
    )


class QuizRequest(BaseModel):

    count: int = Field(
        default=10,
        ge=3,
        le=20,
    )

    difficulty: str = Field(
        default="mixed",
        max_length=20,
    )


# ============================================================
# GET DOCUMENT
# ============================================================

def get_document_or_404(
    document_id: int,
    db: Session,
) -> Document:
    """
    Get a document or return a clean 404 response.
    """

    document = (
        db.query(
            Document
        )
        .filter(
            Document.id == document_id
        )
        .first()
    )

    if not document:

        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    return document


# ============================================================
# GET DOCUMENT CONTENT
# ============================================================

def get_document_context(
    document: Document,
) -> str:
    """
    Build AI context from the document.

    Page information is preserved when available.
    """

    chunks = (
        document.chunks
        if document.chunks
        else []
    )

    if chunks:

        parts = []

        for chunk in chunks:

            page = (
                chunk.page_number
                if chunk.page_number
                else "Unknown"
            )

            content = (
                chunk.content
                if chunk.content
                else ""
            )

            content = content.strip()

            if not content:
                continue

            parts.append(
                (
                    f"DOCUMENT: {document.filename}\n"
                    f"PAGE: {page}\n\n"
                    f"{content}"
                )
            )

        if parts:

            return "\n\n".join(
                parts
            )

    # --------------------------------------------------------
    # Fallback for older documents
    # --------------------------------------------------------

    if document.extracted_text:

        extracted_text = (
            document.extracted_text.strip()
        )

        if extracted_text:

            return (
                f"DOCUMENT: {document.filename}\n\n"
                f"{extracted_text}"
            )

    raise HTTPException(
        status_code=400,
        detail=(
            "This document does not contain "
            "extractable text."
        ),
    )


# ============================================================
# OLLAMA REQUEST
# ============================================================

def generate_ai_response(
    prompt: str,
) -> str:
    """
    Generate an AI response using local Ollama.

    Uses Gemma through the local Ollama service.
    """

    try:

        print("=" * 70)
        print("DOCUMIND AI TOOL REQUEST")
        print("=" * 70)
        print("AI Provider: Ollama")
        print("Model: configured in ai_provider.py")
        print("Local generation: ENABLED")
        print("=" * 70)

        answer = generate_ollama_response(
            prompt
        )

        answer = (
            answer
            if isinstance(answer, str)
            else ""
        ).strip()

        if not answer:

            raise HTTPException(
                status_code=502,
                detail=(
                    "The local AI service returned "
                    "an empty response. Please try again."
                ),
            )

        print("=" * 70)
        print("DOCUMIND AI TOOL SUCCESS")
        print("=" * 70)

        return answer

    except HTTPException:
        raise

    except Exception as error:

        print("=" * 70)
        print("OLLAMA AI TOOL ERROR")
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
                "The local AI service could not "
                "generate the requested result. "
                "Please make sure Ollama is running "
                "and Gemma 3:1B is available."
            ),
        )


# ============================================================
# JSON EXTRACTION
# ============================================================

def extract_json(
    text: str,
) -> Any:
    """
    Extract valid JSON from an AI response.

    Supports:

    - direct JSON
    - markdown JSON code fences
    - JSON embedded in surrounding text
    """

    cleaned = (
        text.strip()
        if isinstance(text, str)
        else ""
    )

    if not cleaned:

        raise HTTPException(
            status_code=502,
            detail=(
                "The AI returned an empty "
                "structured response."
            ),
        )

    # --------------------------------------------------------
    # Remove markdown code fences
    # --------------------------------------------------------

    cleaned = re.sub(
        r"```(?:json)?",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = cleaned.replace(
        "```",
        "",
    ).strip()

    # --------------------------------------------------------
    # Direct JSON
    # --------------------------------------------------------

    try:

        return json.loads(
            cleaned
        )

    except json.JSONDecodeError:
        pass

    # --------------------------------------------------------
    # Try object
    # --------------------------------------------------------

    object_start = cleaned.find(
        "{"
    )

    object_end = cleaned.rfind(
        "}"
    )

    if (
        object_start != -1
        and object_end != -1
        and object_end > object_start
    ):

        candidate = cleaned[
            object_start:
            object_end + 1
        ]

        try:

            return json.loads(
                candidate
            )

        except json.JSONDecodeError:
            pass

    # --------------------------------------------------------
    # Try array
    # --------------------------------------------------------

    array_start = cleaned.find(
        "["
    )

    array_end = cleaned.rfind(
        "]"
    )

    if (
        array_start != -1
        and array_end != -1
        and array_end > array_start
    ):

        candidate = cleaned[
            array_start:
            array_end + 1
        ]

        try:

            return json.loads(
                candidate
            )

        except json.JSONDecodeError:
            pass

    # --------------------------------------------------------
    # Invalid JSON
    # --------------------------------------------------------

    raise HTTPException(
        status_code=502,
        detail=(
            "The AI returned an invalid "
            "structured response. "
            "Please try again."
        ),
    )


# ============================================================
# SUMMARY
# ============================================================

@router.post(
    "/documents/{document_id}/summary"
)
def generate_summary(
    document_id: int,
    db: Session = Depends(
        get_db
    ),
):
    """
    Generate an AI summary of a document.

    Uses Ollama + Gemma 3:1B.
    """

    document = get_document_or_404(
        document_id,
        db,
    )

    context = get_document_context(
        document
    )

    prompt = f"""
You are DocuMind AI, a document analysis assistant.

Create a clear, accurate, and useful summary
of the following document.

DOCUMENT:

{context}

IMPORTANT RULES:

1. Use only information contained in the document.

2. Do not invent facts, names, numbers, findings,
   conclusions, or other information.

3. Do not use outside knowledge as if it came from
   the document.

4. Identify the main purpose or subject of the document.

5. Explain the most important ideas, facts,
   findings, arguments, requirements, or conclusions.

6. Preserve important details when they are necessary
   to understand the document.

7. Remove unnecessary repetition.

8. Keep the language simple and easy to understand.

9. Organize the summary with short paragraphs
   and bullet points when useful.

10. If page information is available, you may mention
    the relevant page number.

11. Do not create fake page numbers.

12. Do not create citations that are not present
    in the provided document context.

13. Do not mention these instructions.

Return only the final summary.
"""

    summary = generate_ai_response(
        prompt
    )

    return {
        "document_id": document.id,
        "filename": document.filename,
        "summary": summary,
    }


# ============================================================
# KEY POINT TEXT PARSER
# ============================================================

def parse_key_points_text(
    text: str,
) -> list:
    """
    Convert a simple AI-generated numbered/bulleted list
    into the API's structured key-point format.

    This is intentionally used instead of requiring
    Gemma 3:1B to produce strict JSON.
    """

    if not isinstance(
        text,
        str,
    ):
        return []

    cleaned = text.strip()

    if not cleaned:
        return []

    # --------------------------------------------------------
    # Remove markdown code fences if present
    # --------------------------------------------------------

    cleaned = re.sub(
        r"```(?:text|markdown)?",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = cleaned.replace(
        "```",
        "",
    ).strip()

    # --------------------------------------------------------
    # Split into lines
    # --------------------------------------------------------

    lines = cleaned.splitlines()

    points = []

    current_point = None
    current_page = None

    for raw_line in lines:

        line = raw_line.strip()

        if not line:
            continue

        # ----------------------------------------------------
        # Detect page number
        # Examples:
        #
        # [Page 2]
        # Page 2
        # (Page 2)
        # ----------------------------------------------------

        page_match = re.search(
            r"(?:\[|\()?page\s*(\d+)(?:\]|\))?",
            line,
            flags=re.IGNORECASE,
        )

        detected_page = None

        if page_match:

            try:

                detected_page = int(
                    page_match.group(1)
                )

            except ValueError:

                detected_page = None

        # ----------------------------------------------------
        # Remove page marker from the text
        # ----------------------------------------------------

        cleaned_line = re.sub(
            r"(?:\s*[\[\(]?\s*page\s*\d+\s*[\]\)]?)",
            "",
            line,
            flags=re.IGNORECASE,
        ).strip()

        # ----------------------------------------------------
        # Detect numbered/bulleted point
        #
        # Examples:
        # 1. Important point
        # 2) Another point
        # - Important point
        # • Important point
        # * Important point
        # ----------------------------------------------------

        point_match = re.match(
            r"^(?:\d+[\.\)]|[-•*])\s*(.+)$",
            cleaned_line,
        )

        if point_match:

            # Save previous point
            if current_point:

                points.append(
                    {
                        "point": current_point.strip(),
                        "page": current_page,
                    }
                )

            current_point = (
                point_match.group(1).strip()
            )

            current_page = detected_page

            continue

        # ----------------------------------------------------
        # If the line is not a new point but we already
        # have a point, treat it as continuation text.
        # ----------------------------------------------------

        if current_point:

            current_point = (
                current_point
                + " "
                + cleaned_line
            ).strip()

            if detected_page is not None:

                current_page = detected_page

            continue

        # ----------------------------------------------------
        # If Gemma did not use bullets at all, treat the
        # line as a possible standalone point.
        # ----------------------------------------------------

        if len(cleaned_line) >= 20:

            points.append(
                {
                    "point": cleaned_line,
                    "page": detected_page,
                }
            )

    # --------------------------------------------------------
    # Save final point
    # --------------------------------------------------------

    if current_point:

        points.append(
            {
                "point": current_point.strip(),
                "page": current_page,
            }
        )

    # --------------------------------------------------------
    # Clean duplicates and empty values
    # --------------------------------------------------------

    validated_points = []

    seen = set()

    for item in points:

        point = item.get(
            "point",
            "",
        )

        if not isinstance(
            point,
            str,
        ):
            continue

        point = point.strip()

        if not point:
            continue

        normalized = (
            point.lower()
        )

        if normalized in seen:
            continue

        seen.add(normalized)

        page = item.get(
            "page"
        )

        if not isinstance(
            page,
            int,
        ):

            page = None

        validated_points.append(
            {
                "point": point,
                "page": page,
            }
        )

    return validated_points


# ============================================================
# KEY POINTS
# ============================================================

@router.post(
    "/documents/{document_id}/key-points"
)
def generate_key_points(
    document_id: int,
    db: Session = Depends(
        get_db
    ),
):
    """
    Generate structured key points.

    Uses Ollama + Gemma 3:1B.

    Gemma is asked for a simple numbered list instead
    of strict JSON because small local models are more
    reliable with natural text output.
    """

    document = get_document_or_404(
        document_id,
        db,
    )

    context = get_document_context(
        document
    )

    prompt = f"""
You are DocuMind AI, a document analysis assistant.

Read the document below and identify the most important
key points.

DOCUMENT:

{context}

IMPORTANT RULES:

1. Use ONLY information contained in the document.

2. Do NOT invent information.

3. Focus on important facts, ideas, findings,
   requirements, definitions, arguments,
   conclusions, dates, names, numbers, and terms.

4. Do not repeat the same idea.

5. Each key point must be concise but informative.

6. Do not use outside knowledge.

7. If a key point clearly comes from a page, include
   the page number at the END of that key point.

8. Never invent a page number.

9. Keep the number of key points reasonable.

10. Use simple English.

11. Do NOT return JSON.

12. Do NOT explain what you are doing.

13. Return ONLY the numbered key points.

Use exactly this style:

1. The first important point. [Page 1]
2. The second important point. [Page 2]
3. The third important point.

If the page number is unknown, do not add one.

Now generate the key points.
"""

    response = generate_ai_response(
        prompt
    )

    print("=" * 70)
    print("KEY POINTS RAW AI RESPONSE")
    print("=" * 70)
    print(response)
    print("=" * 70)

    validated_points = parse_key_points_text(
        response
    )

    # --------------------------------------------------------
    # Fallback:
    # Sometimes Gemma may still return JSON despite being
    # asked for normal text.
    # --------------------------------------------------------

    if not validated_points:

        try:

            data = extract_json(
                response
            )

            if isinstance(
                data,
                list,
            ):

                for item in data:

                    if not isinstance(
                        item,
                        dict,
                    ):
                        continue

                    point = item.get(
                        "point"
                    )

                    if not isinstance(
                        point,
                        str,
                    ):
                        continue

                    point = point.strip()

                    if not point:
                        continue

                    page = item.get(
                        "page"
                    )

                    if not isinstance(
                        page,
                        int,
                    ):
                        page = None

                    validated_points.append(
                        {
                            "point": point,
                            "page": page,
                        }
                    )

        except HTTPException:
            pass

    # --------------------------------------------------------
    # Final validation
    # --------------------------------------------------------

    if not validated_points:

        raise HTTPException(
            status_code=502,
            detail=(
                "The AI did not return usable "
                "key points. Please try again."
            ),
        )

    return {
        "document_id": document.id,
        "filename": document.filename,
        "key_points": validated_points,
    }


# ============================================================
# FLASHCARDS
# ============================================================

@router.post(
    "/documents/{document_id}/flashcards"
)
def generate_flashcards(
    document_id: int,
    request: FlashcardRequest,
    db: Session = Depends(
        get_db
    ),
):
    """
    Generate study flashcards.

    Uses Ollama + Gemma 3:1B.
    """

    document = get_document_or_404(
        document_id,
        db,
    )

    context = get_document_context(
        document
    )

    prompt = f"""
You are DocuMind AI, a document-based study assistant.

Create {request.count} useful study flashcards
based ONLY on the following document.

DOCUMENT:

{context}

IMPORTANT RULES:

1. Use only information contained in the document.

2. Do not invent information.

3. Questions should test meaningful concepts,
   facts, definitions, findings, or important details.

4. Answers should be accurate, concise, and complete.

5. Avoid duplicate questions.

6. Avoid questions whose answers are not clearly
   supported by the document.

7. Include the source page when known.

8. Never invent a page number.

9. Do not create fake citations.

10. Return ONLY valid JSON.

11. Do not include explanations outside the JSON.

Return this structure:

[
  {{
    "question": "What is ...?",
    "answer": "...",
    "page": 1
  }}
]
"""

    response = generate_ai_response(
        prompt
    )

    data = extract_json(
        response
    )

    if not isinstance(
        data,
        list,
    ):

        raise HTTPException(
            status_code=502,
            detail=(
                "The AI returned an invalid "
                "flashcard format."
            ),
        )

    validated_flashcards = []

    for item in data:

        if not isinstance(
            item,
            dict,
        ):
            continue

        question = item.get(
            "question"
        )

        answer = item.get(
            "answer"
        )

        if not isinstance(
            question,
            str,
        ):
            continue

        if not isinstance(
            answer,
            str,
        ):
            continue

        question = question.strip()

        answer = answer.strip()

        if not question or not answer:
            continue

        page = item.get(
            "page"
        )

        if not isinstance(
            page,
            int,
        ):

            page = None

        validated_flashcards.append(
            {
                "question": question,
                "answer": answer,
                "page": page,
            }
        )

    if not validated_flashcards:

        raise HTTPException(
            status_code=502,
            detail=(
                "The AI did not return "
                "valid flashcards."
            ),
        )

    return {
        "document_id": document.id,
        "filename": document.filename,
        "flashcards": validated_flashcards,
    }


# ============================================================
# QUIZ
# ============================================================

@router.post(
    "/documents/{document_id}/quiz"
)
def generate_quiz(
    document_id: int,
    request: QuizRequest,
    db: Session = Depends(
        get_db
    ),
):
    """
    Generate a multiple-choice quiz.

    Uses Ollama + Gemma 3:1B.
    """

    document = get_document_or_404(
        document_id,
        db,
    )

    difficulty = (
        request.difficulty
        .lower()
        .strip()
    )

    allowed_difficulties = {
        "easy",
        "medium",
        "hard",
        "mixed",
    }

    if difficulty not in allowed_difficulties:

        raise HTTPException(
            status_code=400,
            detail=(
                "Difficulty must be "
                "easy, medium, hard, or mixed."
            ),
        )

    context = get_document_context(
        document
    )

    prompt = f"""
You are DocuMind AI, a document-based study assistant.

Create a {difficulty} quiz containing
{request.count} multiple-choice questions
based ONLY on the following document.

DOCUMENT:

{context}

IMPORTANT RULES:

1. Use only information contained in the document.

2. Do not invent information.

3. Every question must have exactly four choices.

4. Only one choice can be correct.

5. The correct answer MUST exactly match
   one of the four options.

6. Include a short explanation.

7. Include the source page when known.

8. Never invent a page number.

9. Avoid ambiguous questions.

10. Do not repeat questions.

11. Make questions meaningful and useful
    for studying.

12. Do not use outside knowledge.

13. Do not create fake citations.

14. Return ONLY valid JSON.

15. Do not include any explanation outside
    the JSON.

Return this exact structure:

[
  {{
    "question": "What is ...?",
    "options": [
      "Option A",
      "Option B",
      "Option C",
      "Option D"
    ],
    "correct_answer": "Option A",
    "explanation": "This is correct because...",
    "page": 1
  }}
]
"""

    response = generate_ai_response(
        prompt
    )

    data = extract_json(
        response
    )

    if not isinstance(
        data,
        list,
    ):

        raise HTTPException(
            status_code=502,
            detail=(
                "The AI returned an invalid "
                "quiz format."
            ),
        )

    validated_questions = []

    for question in data:

        if not isinstance(
            question,
            dict,
        ):
            continue

        question_text = question.get(
            "question"
        )

        options = question.get(
            "options"
        )

        correct_answer = question.get(
            "correct_answer"
        )

        explanation = question.get(
            "explanation",
            "",
        )

        page = question.get(
            "page"
        )

        # ----------------------------------------------------
        # Validate question
        # ----------------------------------------------------

        if not isinstance(
            question_text,
            str,
        ):
            continue

        question_text = (
            question_text.strip()
        )

        if not question_text:
            continue

        # ----------------------------------------------------
        # Validate options
        # ----------------------------------------------------

        if not isinstance(
            options,
            list,
        ):
            continue

        if len(options) != 4:
            continue

        normalized_options = []

        valid_options = True

        for option in options:

            if not isinstance(
                option,
                str,
            ):

                valid_options = False
                break

            cleaned_option = (
                option.strip()
            )

            if not cleaned_option:

                valid_options = False
                break

            normalized_options.append(
                cleaned_option
            )

        if not valid_options:
            continue

        # ----------------------------------------------------
        # Prevent duplicate options
        # ----------------------------------------------------

        if len(
            set(
                normalized_options
            )
        ) != 4:

            continue

        # ----------------------------------------------------
        # Validate correct answer
        # ----------------------------------------------------

        if not isinstance(
            correct_answer,
            str,
        ):
            continue

        correct_answer = (
            correct_answer.strip()
        )

        if (
            correct_answer
            not in normalized_options
        ):

            continue

        # ----------------------------------------------------
        # Validate explanation
        # ----------------------------------------------------

        if not isinstance(
            explanation,
            str,
        ):

            explanation = ""

        explanation = (
            explanation.strip()
        )

        # ----------------------------------------------------
        # Validate page
        # ----------------------------------------------------

        if not isinstance(
            page,
            int,
        ):

            page = None

        # ----------------------------------------------------
        # Add validated question
        # ----------------------------------------------------

        validated_questions.append(
            {
                "question": question_text,
                "options": normalized_options,
                "correct_answer": correct_answer,
                "explanation": explanation,
                "page": page,
            }
        )

    # ========================================================
    # FINAL VALIDATION
    # ========================================================

    if not validated_questions:

        raise HTTPException(
            status_code=502,
            detail=(
                "The AI did not return "
                "valid quiz questions."
            ),
        )

    return {
        "document_id": document.id,
        "filename": document.filename,
        "difficulty": difficulty,
        "questions": validated_questions,
    }