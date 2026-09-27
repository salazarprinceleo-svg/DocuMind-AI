from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    ChatMessage,
    ChatSession,
    Document,
)
from app.llm import generate_response
from app.vector_search import search_documents


router = APIRouter(
    prefix="/api",
    tags=["Chat"],
)


# ============================================================
# REQUEST MODELS
# ============================================================


class ChatRequest(BaseModel):
    session_id: Optional[int] = None

    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
    )

    document_ids: List[int] = Field(
        default_factory=list
    )

    response_style: str = "balanced"

    show_sources: bool = True

    source_count: int = 5

    use_general_knowledge: bool = True

    save_chat_history: bool = True


# ============================================================
# RESPONSE MODELS
# ============================================================


class ChatSource(BaseModel):
    document_id: int

    filename: str

    page_number: Optional[int] = None

    chunk_index: Optional[int] = None

    score: Optional[float] = None


class ChatMessageResponse(BaseModel):
    id: Optional[int] = None

    role: str

    content: str

    created_at: Optional[datetime] = None


class ChatSessionResponse(BaseModel):
    id: int

    title: str

    created_at: Optional[datetime] = None

    updated_at: Optional[datetime] = None


class ChatHistoryResponse(BaseModel):
    session: ChatSessionResponse

    messages: List[
        ChatMessageResponse
    ]


class ChatResponse(BaseModel):
    session_id: int

    message: ChatMessageResponse

    sources: List[ChatSource] = Field(
        default_factory=list
    )


# ============================================================
# QUESTION MODE DETECTION
# ============================================================


DOCUMENT_PHRASES = [
    "according to the document",
    "according to the documents",
    "according to this document",
    "according to this file",
    "according to the file",
    "according to my document",
    "according to my documents",
    "in the document",
    "in this document",
    "in the file",
    "in this file",
    "from the document",
    "from this document",
    "from the file",
    "from this file",
    "based on the document",
    "based on this document",
    "based on the file",
    "based on this file",
    "what does the document say",
    "what does this document say",
    "what does the file say",
    "what does this file say",
    "what is stated in the document",
    "what is stated in this document",
    "what is mentioned in the document",
    "what is mentioned in this document",
    "summarize the document",
    "summarise the document",
    "summarize this document",
    "summarise this document",
    "summarize the file",
    "summarise the file",
    "summarize this file",
    "summarise this file",
    "explain the document",
    "explain this document",
    "explain the file",
    "explain this file",
    "from my uploaded document",
    "from my uploaded file",
]


def detect_question_mode(
    question: str,
) -> str:
    """
    Determines whether the user explicitly asks
    about a document or is asking a general question.

    This is intentionally conservative.

    Example:

        "What is Python?"
            -> general

        "According to the document, what is Python?"
            -> document
    """

    normalized = (
        question.strip()
        .lower()
    )

    for phrase in DOCUMENT_PHRASES:
        if phrase in normalized:
            return "document"

    return "general"


# ============================================================
# RESPONSE CLEANING
# ============================================================


def clean_response(
    response: Any,
) -> str:
    """
    Converts an LLM response into clean text.
    """

    if response is None:
        return ""

    if isinstance(
        response,
        str,
    ):
        return response.strip()

    if isinstance(
        response,
        dict,
    ):
        content = response.get(
            "content"
        )

        if content is not None:
            return str(
                content
            ).strip()

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

            if content is not None:
                return str(
                    content
                ).strip()

    content = getattr(
        response,
        "content",
        None,
    )

    if content is not None:
        return str(
            content
        ).strip()

    return str(
        response
    ).strip()


# ============================================================
# SOURCE BUILDING
# ============================================================


def build_source_objects(
    results: List[Dict[str, Any]],
    source_count: int,
) -> List[ChatSource]:
    """
    Converts vector search results into ChatSource objects.

    IMPORTANT:
    vector_search.py returns flat dictionaries.

    We DO NOT use:

        result.get("document")

    because there is no "document" field.

    Instead we use:

        document_id
        filename
        page_number
        chunk_index
        score
    """

    sources: List[
        ChatSource
    ] = []

    if source_count <= 0:
        return sources

    for result in results[
        :source_count
    ]:
        document_id = result.get(
            "document_id"
        )

        filename = result.get(
            "filename"
        )

        if (
            document_id is None
            or not filename
        ):
            continue

        try:
            clean_document_id = int(
                document_id
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        score = result.get(
            "score"
        )

        try:
            clean_score = (
                float(score)
                if score is not None
                else None
            )
        except (
            TypeError,
            ValueError,
        ):
            clean_score = None

        page_number = result.get(
            "page_number"
        )

        chunk_index = result.get(
            "chunk_index"
        )

        sources.append(
            ChatSource(
                document_id=clean_document_id,
                filename=str(
                    filename
                ),
                page_number=(
                    int(page_number)
                    if page_number is not None
                    else None
                ),
                chunk_index=(
                    int(chunk_index)
                    if chunk_index is not None
                    else None
                ),
                score=clean_score,
            )
        )

    return sources


# ============================================================
# RAG CONTEXT
# ============================================================


def build_context(
    results: List[Dict[str, Any]],
) -> str:
    """
    Converts vector search results into the context
    that will be given to the local AI.

    IMPORTANT:
    This uses the actual shape returned by
    vector_search.py.
    """

    if not results:
        return ""

    context_parts: List[str] = []

    for index, result in enumerate(
        results,
        start=1,
    ):
        filename = str(
            result.get(
                "filename",
                "Unknown document",
            )
        )

        content = str(
            result.get(
                "content",
                "",
            )
        ).strip()

        if not content:
            continue

        page_number = result.get(
            "page_number"
        )

        score = result.get(
            "score",
            0.0,
        )

        if page_number is not None:
            location = (
                f"{filename}, page "
                f"{page_number}"
            )
        else:
            location = filename

        try:
            clean_score = float(
                score
            )
        except (
            TypeError,
            ValueError,
        ):
            clean_score = 0.0

        context_parts.append(
            "\n".join(
                [
                    (
                        f"[Source {index}: "
                        f"{location}]"
                    ),
                    (
                        f"Similarity score: "
                        f"{clean_score:.4f}"
                    ),
                    content,
                    (
                        f"[End Source {index}]"
                    ),
                ]
            )
        )

    return "\n\n".join(
        context_parts
    )


# ============================================================
# PREVIOUS CHAT HISTORY
# ============================================================


def build_previous_messages(
    messages: List[ChatMessage],
    max_messages: int = 10,
) -> str:
    """
    Converts previous chat messages into
    a simple conversation history for the LLM.
    """

    if not messages:
        return ""

    recent_messages = messages[
        -max_messages:
    ]

    history_parts = []

    for message in recent_messages:
        role = getattr(
            message,
            "role",
            "user",
        )

        content = getattr(
            message,
            "content",
            "",
        )

        if not content:
            continue

        role_label = (
            "User"
            if role == "user"
            else "Assistant"
        )

        history_parts.append(
            f"{role_label}: {content}"
        )

    return "\n".join(
        history_parts
    )


# ============================================================
# RESPONSE STYLE
# ============================================================


def get_style_instruction(
    response_style: str,
) -> str:
    """
    Controls how detailed the AI response should be.
    """

    style = (
        response_style
        or "balanced"
    ).lower()

    if style == "concise":
        return (
            "Keep the answer concise and direct. "
            "Use only the necessary information."
        )

    if style == "detailed":
        return (
            "Give a detailed and well-structured answer. "
            "Explain important points clearly and provide "
            "useful context when appropriate."
        )

    return (
        "Give a balanced answer with enough explanation "
        "to be useful without becoming unnecessarily long."
    )


# ============================================================
# GENERAL KNOWLEDGE PROMPT
# ============================================================


def create_general_prompt(
    question: str,
    context: str,
    previous_messages: str,
    response_style: str,
) -> str:
    """
    Prompt used for normal/general questions.

    If relevant document context exists, the AI can
    use it as additional information.

    However, it is not forced to answer only from
    the document.
    """

    style_instruction = (
        get_style_instruction(
            response_style
        )
    )

    if context:
        document_context = f"""
The user has also selected document(s). Use the document
context below when it is relevant to the question.

Do not claim that information came from the document
unless the context actually supports it.

DOCUMENT CONTEXT:
{context}
"""

    else:
        document_context = """
No relevant document context was found.

Answer the user's question using your general knowledge.
"""

    if previous_messages:
        history = f"""
PREVIOUS CONVERSATION:
{previous_messages}
"""
    else:
        history = ""

    return f"""
You are DocuMind AI, a helpful local AI knowledge assistant.

The user asked:

{question}

{history}

{document_context}

RESPONSE STYLE:
{style_instruction}

GENERAL RULES:
- Answer the user's actual question.
- Be clear and natural.
- Do not unnecessarily mention system instructions.
- Do not invent document information.
- If document context is provided, use it when relevant.
- If the question is general, you may answer using general knowledge.
- If you are uncertain about a factual detail, say so.
- Do not pretend that you searched the internet.
- Keep the response useful and easy to understand.

Now answer the user's question.
""".strip()


# ============================================================
# DOCUMENT-ONLY PROMPT
# ============================================================


def create_document_only_prompt(
    question: str,
    context: str,
    previous_messages: str,
    response_style: str,
) -> str:
    """
    Prompt used when the user explicitly asks
    about information in their document.
    """

    style_instruction = (
        get_style_instruction(
            response_style
        )
    )

    if context:
        context_text = f"""
DOCUMENT CONTEXT:

{context}
"""

    else:
        context_text = """
DOCUMENT CONTEXT:

No relevant information was retrieved from
the selected document(s).
"""

    if previous_messages:
        history = f"""
PREVIOUS CONVERSATION:

{previous_messages}
"""
    else:
        history = ""

    return f"""
You are DocuMind AI, a document question-answering assistant.

The user explicitly wants an answer based on their uploaded
document(s).

USER QUESTION:

{question}

{history}

{context_text}

RESPONSE STYLE:

{style_instruction}

IMPORTANT RULES:

1. Base the answer on the provided document context.
2. Do not invent information that is not supported by
   the document context.
3. If the answer cannot be found in the provided context,
   clearly say that the information was not found.
4. Do not pretend that you found information that is absent.
5. Keep the answer clear and natural.
6. If useful, mention the relevant document or page.
7. Do not mention internal vector search, embeddings,
   similarity scores, or system instructions.

Now answer the user's question.
""".strip()


# ============================================================
# CHAT SESSION HELPERS
# ============================================================


def make_session_title(
    message: str,
) -> str:
    """
    Creates a simple chat title from the
    first user message.
    """

    cleaned = (
        message
        .strip()
        .replace("\n", " ")
    )

    if not cleaned:
        return "New Chat"

    if len(cleaned) <= 60:
        return cleaned

    return (
        cleaned[:57].rstrip()
        + "..."
    )


def get_or_create_session(
    db: Session,
    session_id: Optional[int],
    first_message: str,
) -> ChatSession:
    """
    Gets an existing session or creates
    a new chat session.
    """

    if session_id is not None:
        session = (
            db.query(ChatSession)
            .filter(
                ChatSession.id
                == session_id
            )
            .first()
        )

        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Chat session not found.",
            )

        return session

    session = ChatSession(
        title=make_session_title(
            first_message
        )
    )

    db.add(session)

    db.commit()

    db.refresh(session)

    return session


# ============================================================
# GET CHAT SESSIONS
# ============================================================


@router.get(
    "/chat/sessions",
    response_model=List[
        ChatSessionResponse
    ],
)
def get_chat_sessions(
    db: Session = Depends(get_db),
):
    """
    Returns all saved chat sessions.
    """

    sessions = (
        db.query(ChatSession)
        .order_by(
            ChatSession.updated_at.desc()
        )
        .all()
    )

    return [
        ChatSessionResponse(
            id=session.id,
            title=session.title
            or "New Chat",
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
        for session in sessions
    ]


# ============================================================
# CREATE CHAT SESSION
# ============================================================


@router.post(
    "/chat/sessions",
    response_model=ChatSessionResponse,
)
def create_chat_session(
    db: Session = Depends(get_db),
):
    """
    Creates a new empty chat session.
    """

    session = ChatSession(
        title="New Chat"
    )

    db.add(session)

    db.commit()

    db.refresh(session)

    return ChatSessionResponse(
        id=session.id,
        title=session.title
        or "New Chat",
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


# ============================================================
# GET CHAT HISTORY
# ============================================================


@router.get(
    "/chat/sessions/{session_id}",
    response_model=ChatHistoryResponse,
)
def get_chat_history(
    session_id: int,
    db: Session = Depends(get_db),
):
    """
    Returns the selected chat session
    and its messages.
    """

    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id
            == session_id
        )
        .first()
    )

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Chat session not found.",
        )

    messages = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.session_id
            == session_id
        )
        .order_by(
            ChatMessage.created_at.asc()
        )
        .all()
    )

    return ChatHistoryResponse(
        session=ChatSessionResponse(
            id=session.id,
            title=session.title
            or "New Chat",
            created_at=session.created_at,
            updated_at=session.updated_at,
        ),
        messages=[
            ChatMessageResponse(
                id=message.id,
                role=message.role,
                content=message.content,
                created_at=message.created_at,
            )
            for message in messages
        ],
    )


# ============================================================
# DELETE CHAT SESSION
# ============================================================


@router.delete(
    "/chat/sessions/{session_id}",
)
def delete_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
):
    """
    Deletes a chat session and its messages.
    """

    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id
            == session_id
        )
        .first()
    )

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Chat session not found.",
        )

    (
        db.query(ChatMessage)
        .filter(
            ChatMessage.session_id
            == session_id
        )
        .delete(
            synchronize_session=False
        )
    )

    db.delete(session)

    db.commit()

    return {
        "message": "Chat session deleted successfully."
    }


# ============================================================
# SEND CHAT MESSAGE
# ============================================================


@router.post(
    "/chat",
    response_model=ChatResponse,
)
def send_chat_message(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    """
    Main DocuMind AI chat endpoint.

    Supports:

    - General questions
    - Document questions
    - Selected documents
    - RAG context
    - Local Ollama AI
    - Chat history
    - Sources
    """

    # --------------------------------------------------------
    # Validate question
    # --------------------------------------------------------

    question = (
        request.message
        .strip()
    )

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    # --------------------------------------------------------
    # Validate source count
    # --------------------------------------------------------

    source_count = max(
        0,
        min(
            int(
                request.source_count
            ),
            20,
        ),
    )

    # --------------------------------------------------------
    # Create or get session
    # --------------------------------------------------------

    session = get_or_create_session(
        db=db,
        session_id=request.session_id,
        first_message=question,
    )

    # --------------------------------------------------------
    # Load previous messages
    # --------------------------------------------------------

    previous_messages: List[
        ChatMessage
    ] = []

    if request.save_chat_history:
        previous_messages = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.session_id
                == session.id
            )
            .order_by(
                ChatMessage.created_at.asc()
            )
            .all()
        )

    previous_history = (
        build_previous_messages(
            previous_messages
        )
    )

    # --------------------------------------------------------
    # Detect question mode
    # --------------------------------------------------------

    question_mode = detect_question_mode(
        question
    )

    print("=" * 70)
    print("DOCUMIND CHAT REQUEST")
    print("=" * 70)

    print(
        "Session ID:",
        session.id,
    )

    print(
        "Question:",
        question,
    )

    print(
        "Question mode:",
        question_mode,
    )

    print(
        "Selected document IDs:",
        request.document_ids,
    )

    print(
        "General knowledge:",
        request.use_general_knowledge,
    )

    print("=" * 70)

    # --------------------------------------------------------
    # Validate selected documents
    # --------------------------------------------------------

    selected_document_ids: List[int] = []

    if request.document_ids:
        try:
            selected_document_ids = list(
                dict.fromkeys(
                    int(document_id)
                    for document_id
                    in request.document_ids
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

    selected_documents: List[
        Document
    ] = []

    if selected_document_ids:

        selected_documents = (
            db.query(Document)
            .filter(
                Document.id.in_(
                    selected_document_ids
                )
            )
            .all()
        )

        found_ids = {
            document.id
            for document in selected_documents
        }

        missing_ids = [
            document_id
            for document_id
            in selected_document_ids
            if document_id
            not in found_ids
        ]

        if missing_ids:
            print(
                "WARNING: Some selected document IDs "
                "were not found:",
                missing_ids,
            )

    # --------------------------------------------------------
    # Search selected documents
    # --------------------------------------------------------

    search_results: List[
        Dict[str, Any]
    ] = []

    if selected_document_ids:

        print("=" * 70)
        print("SEARCHING SELECTED DOCUMENTS")
        print("=" * 70)

        try:
            search_results = search_documents(
                db=db,
                query=question,
                document_ids=selected_document_ids,
                top_k=8,
            )

        except HTTPException:
            raise

        except Exception as error:
            print("=" * 70)
            print("DOCUMENT SEARCH ERROR")
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
                    "Document search failed. "
                    "Please make sure your document "
                    "has been processed and embedded."
                ),
            )

    # --------------------------------------------------------
    # IMPORTANT FIX
    #
    # Do NOT filter results again using score >= 0.15.
    #
    # vector_search.py already:
    #
    # 1. Calculates similarity
    # 2. Applies minimum score
    # 3. Falls back to the best available chunks
    #
    # Filtering them again here can throw away useful
    # document context.
    # --------------------------------------------------------

    document_results = search_results

    # --------------------------------------------------------
    # Build RAG context
    # --------------------------------------------------------

    context = build_context(
        document_results
    )

    print("=" * 70)
    print("RAG CONTEXT")
    print("=" * 70)

    print(
        "Search result count:",
        len(document_results),
    )

    print(
        "Context length:",
        len(context),
    )

    if context:
        print(
            "Document context successfully created."
        )
    else:
        print(
            "No document context was created."
        )

    print("=" * 70)

    # --------------------------------------------------------
    # Check general knowledge setting
    # --------------------------------------------------------

    if (
        not request.use_general_knowledge
        and not selected_document_ids
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "General knowledge is disabled. "
                "Please enable General Knowledge in "
                "Settings or select a document."
            ),
        )

    # --------------------------------------------------------
    # Create prompt
    # --------------------------------------------------------

    if question_mode == "document":

        prompt = create_document_only_prompt(
            question=question,
            context=context,
            previous_messages=previous_history,
            response_style=request.response_style,
        )

    elif request.use_general_knowledge:

        prompt = create_general_prompt(
            question=question,
            context=context,
            previous_messages=previous_history,
            response_style=request.response_style,
        )

    elif context:

        prompt = create_document_only_prompt(
            question=question,
            context=context,
            previous_messages=previous_history,
            response_style=request.response_style,
        )

    else:

        prompt = create_document_only_prompt(
            question=question,
            context="",
            previous_messages=previous_history,
            response_style=request.response_style,
        )

    # --------------------------------------------------------
    # Generate AI response
    # --------------------------------------------------------

    print("=" * 70)
    print("GENERATING LOCAL AI RESPONSE")
    print("=" * 70)

    try:

        raw_response = generate_response(
            prompt
        )

    except HTTPException:
        raise

    except Exception as error:

        print("=" * 70)
        print("LOCAL AI GENERATION ERROR")
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
                "generate a response. "
                "Please make sure Ollama is running "
                "and the configured model is available."
            ),
        )

    answer = clean_response(
        raw_response
    )

    if not answer:
        raise HTTPException(
            status_code=503,
            detail=(
                "The local AI returned an empty response."
            ),
        )

    print(
        "Response length:",
        len(answer),
    )

    print("=" * 70)

    # --------------------------------------------------------
    # Save user message
    # --------------------------------------------------------

    if request.save_chat_history:

        user_message = ChatMessage(
            session_id=session.id,
            role="user",
            content=question,
        )

        db.add(
            user_message
        )

    # --------------------------------------------------------
    # Save assistant message
    # --------------------------------------------------------

    if request.save_chat_history:

        assistant_message = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=answer,
        )

        db.add(
            assistant_message
        )

        # Update session title if this is the
        # first meaningful message.
        if (
            not session.title
            or session.title
            == "New Chat"
        ):
            session.title = (
                make_session_title(
                    question
                )
            )

        session.updated_at = (
            datetime.utcnow()
        )

        db.commit()

        db.refresh(
            assistant_message
        )

        response_message = (
            assistant_message
        )

    else:

        # When history saving is disabled,
        # we still return a temporary response
        # object to the frontend.
        response_message = None

    # --------------------------------------------------------
    # Build response sources
    # --------------------------------------------------------

    sources: List[
        ChatSource
    ] = []

    if request.show_sources:

        sources = build_source_objects(
            document_results,
            source_count,
        )

    # --------------------------------------------------------
    # Final response
    # --------------------------------------------------------

    if response_message is not None:

        response_message_data = (
            ChatMessageResponse(
                id=response_message.id,
                role=response_message.role,
                content=response_message.content,
                created_at=response_message.created_at,
            )
        )

    else:

        response_message_data = (
            ChatMessageResponse(
                id=None,
                role="assistant",
                content=answer,
                created_at=datetime.utcnow(),
            )
        )

    print("=" * 70)
    print("DOCUMIND CHAT SUCCESS")
    print("=" * 70)

    print(
        "Session ID:",
        session.id,
    )

    print(
        "Sources:",
        len(sources),
    )

    print("=" * 70)

    return ChatResponse(
        session_id=session.id,
        message=response_message_data,
        sources=sources,
    )