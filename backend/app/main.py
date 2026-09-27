from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import HTTPException

from app.database import engine, Base

from app.auth import (
    router as auth_router
)

from app.documents import (
    router as documents_router
)

from app.chat import (
    router as chat_router
)

from app.ai_tools import (
    router as ai_tools_router
)

import app.models


# ============================================================
# DATABASE
# ============================================================

Base.metadata.create_all(
    bind=engine
)


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="DocuMind AI",
    description=(
        "AI-powered document and knowledge assistant"
    ),
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],

    allow_credentials=True,

    allow_methods=[
        "*"
    ],

    allow_headers=[
        "*"
    ],
)


# ============================================================
# HTTP EXCEPTION HANDLER
# ============================================================

@app.exception_handler(
    HTTPException
)
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
):
    """
    Handle expected HTTP errors such as:
    400 Bad Request
    401 Unauthorized
    403 Forbidden
    404 Not Found
    422 Unprocessable Entity
    503 Service Unavailable

    Keeps the API response format consistent.
    """

    detail = exc.detail

    if isinstance(detail, str):
        message = detail
    else:
        message = "The request could not be completed."

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "request_error",
            "detail": message,
        },
    )


# ============================================================
# VALIDATION ERROR HANDLER
# ============================================================

@app.exception_handler(
    RequestValidationError
)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    """
    Return a clean and consistent response when
    FastAPI/Pydantic request validation fails.
    """

    errors = []

    for error in exc.errors():

        location = "request"

        if error.get("loc"):

            location = ".".join(
                str(item)
                for item in error["loc"]
            )

        message = error.get(
            "msg",
            "Invalid value.",
        )

        errors.append(
            {
                "field": location,
                "message": message,
            }
        )

    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "detail": (
                "The request contains invalid "
                "or missing information."
            ),
            "errors": errors,
        },
    )


# ============================================================
# GENERAL EXCEPTION HANDLER
# ============================================================

@app.exception_handler(
    Exception
)
async def general_exception_handler(
    request: Request,
    exc: Exception,
):
    """
    Catch unexpected backend errors.

    Internal exception details are intentionally NOT
    returned to the frontend.
    """

    print("=" * 70)
    print("UNEXPECTED SERVER ERROR")
    print("=" * 70)

    print(
        "Path:",
        request.url.path,
    )

    print(
        "Method:",
        request.method,
    )

    print(
        "Error type:",
        type(exc).__name__,
    )

    print(
        "Error:",
        str(exc),
    )

    print("=" * 70)

    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "detail": (
                "Something went wrong on the server. "
                "Please try again."
            ),
        },
    )


# ============================================================
# AUTHENTICATION ROUTER
# ============================================================

app.include_router(
    auth_router
)


# ============================================================
# DOCUMENT ROUTER
# ============================================================

app.include_router(
    documents_router
)


# ============================================================
# CHAT ROUTER
# ============================================================

app.include_router(
    chat_router
)


# ============================================================
# AI LEARNING TOOLS ROUTER
# ============================================================

app.include_router(
    ai_tools_router
)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "message": (
            "DocuMind AI API is running!"
        ),
        "status": "success",
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health_check():

    return {
        "status": "healthy"
    }