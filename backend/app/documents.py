import json
import uuid

from datetime import datetime
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)

from fastapi.responses import FileResponse

from sqlalchemy import or_
from sqlalchemy.orm import Session

from pypdf import PdfReader

from app.database import get_db

from app.models import (
    Document,
    DocumentChunk,
)

from app.chunking import (
    create_page_chunks,
)

from app.document_processing import (
    combine_page_text,
    extract_document_pages,
)

from app.embeddings import (
    create_embedding,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/api/documents",
    tags=["Documents"],
)


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

UPLOAD_DIR = BASE_DIR / "uploads"

MAX_FILE_SIZE = 10 * 1024 * 1024


# ============================================================
# ALLOWED FILE TYPES
# ============================================================

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".pptx",
    ".txt",
}


ALLOWED_CONTENT_TYPES = {
    ".pdf": {
        "application/pdf",
        "application/octet-stream",
    },

    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    },

    ".xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/octet-stream",
    },

    ".pptx": {
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/octet-stream",
    },

    ".txt": {
        "text/plain",
        "application/octet-stream",
    },
}


# ============================================================
# CREATE UPLOAD DIRECTORY
# ============================================================

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_file_extension(
    filename: str,
) -> str:
    """
    Return a normalized lowercase file extension.
    """

    return Path(
        filename
    ).suffix.lower()


def get_file_size(
    file_path: str | Path | None,
) -> int:
    """
    Safely return the physical file size.
    """

    if not file_path:
        return 0

    try:
        path = Path(file_path)

        if not path.exists():
            return 0

        return path.stat().st_size

    except OSError:
        return 0


def get_media_type(
    filename: str,
) -> str:
    """
    Return the correct response media type
    for downloading the original file.
    """

    extension = get_file_extension(
        filename
    )

    if extension == ".pdf":
        return "application/pdf"

    if extension == ".docx":
        return (
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        )

    if extension == ".xlsx":
        return (
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )

    if extension == ".pptx":
        return (
            "application/vnd.openxmlformats-officedocument."
            "presentationml.presentation"
        )

    if extension == ".txt":
        return "text/plain"

    return "application/octet-stream"


def delete_file_safely(
    file_path: str | Path | None,
) -> bool:
    """
    Safely delete a physical file.

    Returns True if the file was deleted or
    did not exist.

    Returns False if deletion failed.
    """

    if not file_path:
        return True

    try:
        path = Path(
            file_path
        )

        if not path.exists():
            return True

        path.unlink()

        return True

    except OSError as error:

        print(
            "FILE DELETE ERROR:",
            type(error).__name__,
            str(error),
        )

        return False


def is_safe_upload_path(
    file_path: str | Path,
) -> bool:
    """
    Make sure the supplied path stays inside
    the application's upload directory.
    """

    try:

        upload_root = UPLOAD_DIR.resolve()

        target = Path(
            file_path
        ).resolve()

        return (
            target == upload_root
            or upload_root in target.parents
        )

    except OSError:

        return False


def safe_processing_error(
    operation: str,
) -> HTTPException:
    """
    Return a user-safe document processing error.

    Internal exception details are not exposed.
    """

    return HTTPException(
        status_code=400,
        detail=(
            f"Could not {operation}. "
            "Please make sure the document is valid, "
            "readable, and not corrupted."
        ),
    )


# ============================================================
# DOCUMENT PROCESSING STATUS
# ============================================================

def is_document_processed(
    document: Document,
) -> bool:
    """
    Determine whether a document has been completely
    processed and is ready for AI document search.

    A document is considered processed only when:

    - It has at least one page.
    - Extracted text exists.
    - At least one chunk exists.
    - Every chunk has a stored embedding.

    This is important for RAG because a document can have
    extracted text and chunks but still be unusable by
    vector search if embeddings were not created.
    """

    # --------------------------------------------------------
    # Page count
    # --------------------------------------------------------

    if not document.page_count:
        return False

    if document.page_count <= 0:
        return False

    # --------------------------------------------------------
    # Extracted text
    # --------------------------------------------------------

    if not document.extracted_text:
        return False

    if not document.extracted_text.strip():
        return False

    # --------------------------------------------------------
    # Chunks
    # --------------------------------------------------------

    if not document.chunks:
        return False

    # --------------------------------------------------------
    # Embeddings
    # --------------------------------------------------------

    for chunk in document.chunks:

        if not chunk.embedding:
            return False

        if not str(
            chunk.embedding
        ).strip():

            return False

    return True


def get_processing_status(
    document: Document,
) -> str:
    """
    Return a simple processing status.

    A document is "processed" only when it has
    usable stored embeddings.
    """

    if is_document_processed(
        document
    ):
        return "processed"

    return "pending"


# ============================================================
# VALIDATE PDF
# ============================================================

def validate_pdf(
    file_path: str | Path,
) -> None:
    """
    Validate that a PDF can be opened and contains pages.
    """

    try:

        reader = PdfReader(
            str(file_path)
        )

        page_count = len(
            reader.pages
        )

        if page_count <= 0:

            raise ValueError(
                "PDF contains no pages."
            )

    except Exception as error:

        raise ValueError(
            "Invalid PDF."
        ) from error


# ============================================================
# PROCESS DOCUMENT INTERNAL FUNCTION
# ============================================================

def process_document(
    document: Document,
    db: Session,
    keep_file: bool = True,
):
    """
    Extract, chunk, embed, and save a document.

    Shared by:
    - automatic upload processing
    - manual processing
    """

    if not document.file_path:

        raise safe_processing_error(
            "process the document"
        )

    file_path = Path(
        document.file_path
    )

    if not is_safe_upload_path(
        file_path
    ):

        raise HTTPException(
            status_code=500,
            detail="The stored file path is invalid.",
        )

    if not file_path.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "The original file is no longer "
                "available for processing."
            ),
        )

    file_extension = get_file_extension(
        document.filename
    )

    try:

        # ----------------------------------------------------
        # Validate PDF
        # ----------------------------------------------------

        if file_extension == ".pdf":

            validate_pdf(
                file_path
            )

        # ----------------------------------------------------
        # Extract page/sheet/slide-aware text
        # ----------------------------------------------------

        print("=" * 70)
        print("DOCUMENT PROCESSING STARTED")
        print("=" * 70)
        print(
            "Document:",
            document.filename,
        )
        print(
            "Extension:",
            file_extension,
        )

        pages = extract_document_pages(
            str(file_path)
        )

        print(
            "Extracted logical pages:",
            len(pages),
        )

        if not pages:

            raise ValueError(
                "No pages found."
            )

        # ----------------------------------------------------
        # Combine extracted text
        # ----------------------------------------------------

        extracted_text = combine_page_text(
            pages
        )

        print(
            "Extracted text length:",
            len(extracted_text),
        )

        if not extracted_text.strip():

            raise ValueError(
                "No readable text found."
            )

        # ----------------------------------------------------
        # Create chunks
        # ----------------------------------------------------

        chunks = create_page_chunks(
            pages
        )

        print(
            "Created chunks:",
            len(chunks),
        )

        if not chunks:

            raise ValueError(
                "No readable chunks created."
            )

        # ----------------------------------------------------
        # Determine logical page count
        # ----------------------------------------------------

        if file_extension in {
            ".pdf",
            ".pptx",
            ".xlsx",
        }:

            page_count = len(
                pages
            )

        else:

            page_count = 1

        # ----------------------------------------------------
        # Remove old chunks if re-processing
        # ----------------------------------------------------

        existing_chunks = (
            db.query(
                DocumentChunk
            )
            .filter(
                DocumentChunk.document_id
                == document.id
            )
            .all()
        )

        print(
            "Existing chunks to remove:",
            len(existing_chunks),
        )

        for old_chunk in existing_chunks:

            db.delete(
                old_chunk
            )

        db.flush()

        # ----------------------------------------------------
        # Update document information
        # ----------------------------------------------------

        document.page_count = page_count

        document.text_length = len(
            extracted_text
        )

        document.extracted_text = (
            extracted_text
        )

        # ----------------------------------------------------
        # Create chunks and embeddings
        # ----------------------------------------------------

        successful_embeddings = 0

        for chunk_number, chunk_data in enumerate(
            chunks,
            start=1,
        ):

            chunk_content = (
                chunk_data["content"]
            )

            if not chunk_content.strip():

                print(
                    f"Skipping empty chunk "
                    f"{chunk_number}/{len(chunks)}"
                )

                continue

            print("-" * 70)
            print(
                f"Creating Ollama embedding "
                f"{chunk_number}/{len(chunks)}"
            )
            print(
                "Chunk characters:",
                len(chunk_content),
            )

            # ------------------------------------------------
            # Generate embedding
            # ------------------------------------------------

            embedding = create_embedding(
                chunk_content
            )

            # ------------------------------------------------
            # Validate embedding
            # ------------------------------------------------

            if not embedding:

                raise ValueError(
                    f"Ollama returned an empty embedding "
                    f"for chunk {chunk_number}."
                )

            if not isinstance(
                embedding,
                list,
            ):

                embedding = list(
                    embedding
                )

            if len(embedding) == 0:

                raise ValueError(
                    f"Ollama returned a zero-length embedding "
                    f"for chunk {chunk_number}."
                )

            print(
                "Embedding dimensions:",
                len(embedding),
            )

            embedding_json = json.dumps(
                embedding
            )

            # ------------------------------------------------
            # Create database chunk
            # ------------------------------------------------

            chunk = DocumentChunk(
                document_id=document.id,

                chunk_index=chunk_data[
                    "chunk_index"
                ],

                content=chunk_content,

                page_number=chunk_data[
                    "page_number"
                ],

                embedding=embedding_json,
            )

            db.add(
                chunk
            )

            successful_embeddings += 1

        # ----------------------------------------------------
        # Verify embeddings were created
        # ----------------------------------------------------

        if successful_embeddings == 0:

            raise ValueError(
                "No embeddings were created."
            )

        if successful_embeddings != len(chunks):

            raise ValueError(
                "Not all document chunks received "
                "embeddings."
            )

        print("-" * 70)
        print(
            "Successfully created embeddings:",
            successful_embeddings,
        )

        # ----------------------------------------------------
        # Save everything
        # ----------------------------------------------------

        db.commit()

        db.refresh(
            document
        )

        print("=" * 70)
        print("DOCUMENT PROCESSING SUCCESS")
        print("=" * 70)
        print(
            "Document:",
            document.filename,
        )
        print(
            "Pages:",
            page_count,
        )
        print(
            "Text length:",
            len(extracted_text),
        )
        print(
            "Chunks:",
            len(chunks),
        )
        print(
            "Embeddings:",
            successful_embeddings,
        )
        print("=" * 70)

        # ----------------------------------------------------
        # Delete original file when requested
        # ----------------------------------------------------

        file_deleted = False

        if not keep_file:

            file_deleted = delete_file_safely(
                file_path
            )

            if not file_deleted:

                print(
                    "WARNING: Document was processed "
                    "successfully, but the original file "
                    "could not be deleted."
                )

        return {
            "page_count": page_count,

            "text_length": len(
                extracted_text
            ),

            "chunk_count": len(
                chunks
            ),

            "embedding_count": successful_embeddings,

            "file_deleted": file_deleted,
        }

    except HTTPException:

        db.rollback()

        raise

    except Exception as error:

        db.rollback()

        print("=" * 70)
        print("DOCUMENT PROCESSING ERROR")
        print("=" * 70)

        print(
            "Document:",
            document.filename,
        )

        print(
            "Error type:",
            type(error).__name__,
        )

        print(
            "Error:",
            str(error),
        )

        print("=" * 70)

        raise safe_processing_error(
            "process the document"
        )


# ============================================================
# CREATE DOCUMENT RESPONSE
# ============================================================

def document_response(
    document: Document,
    message: str,
    file_size: int | None = None,
):
    """
    Build a consistent API response for a document.
    """

    extension = get_file_extension(
        document.filename
    )

    chunk_count = len(
        document.chunks
    )

    embedding_count = sum(
        1
        for chunk in document.chunks
        if chunk.embedding
    )

    if file_size is None:

        file_size = get_file_size(
            document.file_path
        )

    processed = is_document_processed(
        document
    )

    return {
        "message": message,

        "document": {
            "id": document.id,

            "filename": document.filename,

            "stored_filename":
                document.stored_filename,

            "file_path":
                document.file_path,

            "page_count":
                document.page_count or 0,

            "text_length":
                document.text_length or 0,

            "uploaded_at": (
                document.uploaded_at.isoformat()
                if document.uploaded_at
                else datetime.utcnow().isoformat()
            ),

            "file_extension":
                extension,

            "file_size":
                file_size,

            "chunk_count":
                chunk_count,

            "embedding_count":
                embedding_count,

            "processing_status": (
                "processed"
                if processed
                else "pending"
            ),

            "file_available": bool(
                document.file_path
                and Path(
                    document.file_path
                ).exists()
            ),

            "extracted_text": (
                document.extracted_text
                or ""
            ),
        },
    }


# ============================================================
# UPLOAD DOCUMENT
# ============================================================

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),

    auto_process: bool = Form(
        default=True
    ),

    keep_file: bool = Form(
        default=True
    ),

    db: Session = Depends(
        get_db
    ),
):
    """
    Upload a document.

    auto_process=True:
        Upload + extract + chunk + embed immediately.

    auto_process=False:
        Save the original file as pending.

    keep_file=True:
        Keep the original uploaded file.

    keep_file=False:
        Delete the original file after successful processing.

    When auto_process=False, the original file is temporarily
    kept because it is required for later processing.
    """

    # ========================================================
    # VALIDATE FILENAME
    # ========================================================

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="No file selected.",
        )

    original_filename = Path(
        file.filename
    ).name

    if not original_filename:

        raise HTTPException(
            status_code=400,
            detail="Invalid filename.",
        )

    # ========================================================
    # VALIDATE EXTENSION
    # ========================================================

    file_extension = get_file_extension(
        original_filename
    )

    if file_extension not in ALLOWED_EXTENSIONS:

        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported file type. "
                "Supported files are "
                "PDF, DOCX, XLSX, PPTX, and TXT."
            ),
        )

    # ========================================================
    # VALIDATE MIME TYPE
    # ========================================================

    content_type = (
        file.content_type or ""
    ).lower().strip()

    allowed_types = ALLOWED_CONTENT_TYPES[
        file_extension
    ]

    if (
        content_type
        and content_type not in allowed_types
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "The uploaded file type does not "
                "match its file extension."
            ),
        )

    # ========================================================
    # READ FILE
    # ========================================================

    try:

        contents = await file.read()

    except Exception as error:

        print(
            "UPLOAD READ ERROR:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=400,
            detail="Could not read the uploaded file.",
        )

    # ========================================================
    # CHECK EMPTY FILE
    # ========================================================

    if not contents:

        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    # ========================================================
    # CHECK FILE SIZE
    # ========================================================

    file_size = len(
        contents
    )

    if file_size > MAX_FILE_SIZE:

        raise HTTPException(
            status_code=413,
            detail=(
                "File is too large. "
                "Maximum allowed size is 10 MB."
            ),
        )

    # ========================================================
    # CREATE SAFE STORAGE NAME
    # ========================================================

    storage_id = str(
        uuid.uuid4()
    )

    stored_filename = (
        f"{storage_id}"
        f"{file_extension}"
    )

    file_path = (
        UPLOAD_DIR /
        stored_filename
    )

    # ========================================================
    # VERIFY SAFE PATH
    # ========================================================

    if not is_safe_upload_path(
        file_path
    ):

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not create a safe "
                "upload location."
            ),
        )

    # ========================================================
    # SAVE PHYSICAL FILE
    # ========================================================

    try:

        with file_path.open(
            "wb"
        ) as buffer:

            buffer.write(
                contents
            )

    except OSError as error:

        print(
            "FILE SAVE ERROR:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not save the uploaded file. "
                "Please try again."
            ),
        )

    # ========================================================
    # CREATE DATABASE RECORD
    # ========================================================

    document = Document(
        filename=original_filename,

        stored_filename=stored_filename,

        file_path=str(file_path),

        page_count=0,

        text_length=0,

        extracted_text=None,

        uploaded_at=datetime.utcnow(),
    )

    try:

        db.add(
            document
        )

        db.commit()

        db.refresh(
            document
        )

    except Exception as error:

        db.rollback()

        delete_file_safely(
            file_path
        )

        print(
            "DOCUMENT CREATE ERROR:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not save the uploaded "
                "document record."
            ),
        )

    # ========================================================
    # MANUAL PROCESSING MODE
    # ========================================================

    if not auto_process:

        return document_response(
            document=document,

            message=(
                "Document uploaded successfully. "
                "Processing is waiting for manual action."
            ),

            file_size=file_size,
        )

    # ========================================================
    # AUTOMATIC PROCESSING
    # ========================================================

    try:

        processing_result = process_document(
            document=document,
            db=db,
            keep_file=keep_file,
        )

        return document_response(
            document=document,

            message=(
                "Document uploaded, extracted, "
                "chunked, and embedded successfully."
            ),

            file_size=(
                file_size
                if keep_file
                else 0
            ),
        )

    except HTTPException:

        # ----------------------------------------------------
        # Processing failed.
        # Remove the pending database record.
        # ----------------------------------------------------

        try:

            db.delete(
                document
            )

            db.commit()

        except Exception:

            db.rollback()

        delete_file_safely(
            file_path
        )

        raise

    except Exception as error:

        try:

            db.delete(
                document
            )

            db.commit()

        except Exception:

            db.rollback()

        delete_file_safely(
            file_path
        )

        print(
            "AUTO PROCESSING ERROR:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not process the uploaded document."
            ),
        )


# ============================================================
# PROCESS PENDING DOCUMENT
# ============================================================

@router.post(
    "/{document_id}/process"
)
def process_pending_document(
    document_id: int,

    keep_file: bool = Query(
        default=True
    ),

    db: Session = Depends(
        get_db
    ),
):
    """
    Manually process a pending document.
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

    if is_document_processed(
        document
    ):

        return document_response(
            document=document,

            message=(
                "This document has already been processed."
            ),
        )

    try:

        file_size = get_file_size(
            document.file_path
        )

        process_document(
            document=document,
            db=db,
            keep_file=keep_file,
        )

        return document_response(
            document=document,

            message=(
                "Document processed successfully."
            ),

            file_size=(
                file_size
                if keep_file
                else 0
            ),
        )

    except HTTPException:

        raise

    except Exception as error:

        print(
            "MANUAL PROCESS ERROR:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not process the document. "
                "Please try again."
            ),
        )


# ============================================================
# GET ALL DOCUMENTS
# ============================================================

@router.get("")
def get_documents(
    search: str | None = Query(
        default=None
    ),

    db: Session = Depends(
        get_db
    ),
):
    """
    Return all stored documents.
    """

    try:

        query = db.query(
            Document
        )

        if search:

            cleaned_search = (
                search.strip()
            )

            if cleaned_search:

                search_term = (
                    f"%{cleaned_search}%"
                )

                query = query.filter(
                    or_(
                        Document.filename.ilike(
                            search_term
                        ),

                        Document.extracted_text.ilike(
                            search_term
                        ),
                    )
                )

        documents = (
            query
            .order_by(
                Document.uploaded_at.desc()
            )
            .all()
        )

        results = []

        for document in documents:

            file_size = get_file_size(
                document.file_path
            )

            extension = get_file_extension(
                document.filename
            )

            chunk_count = len(
                document.chunks
            )

            embedding_count = sum(
                1
                for chunk in document.chunks
                if chunk.embedding
            )

            results.append(
                {
                    "id":
                        document.id,

                    "filename":
                        document.filename,

                    "stored_filename":
                        document.stored_filename,

                    "file_path":
                        document.file_path,

                    "page_count":
                        document.page_count or 0,

                    "text_length":
                        document.text_length or 0,

                    "chunk_count":
                        chunk_count,

                    "embedding_count":
                        embedding_count,

                    "uploaded_at":
                        document.uploaded_at.isoformat(),

                    "file_extension":
                        extension,

                    "file_size":
                        file_size,

                    "processing_status":
                        get_processing_status(
                            document
                        ),

                    "file_available":
                        bool(
                            document.file_path
                            and Path(
                                document.file_path
                            ).exists()
                        ),
                }
            )

        return results

    except Exception as error:

        print(
            "GET DOCUMENTS ERROR:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not load the document library. "
                "Please try again."
            ),
        )


# ============================================================
# GET DOCUMENT STATISTICS
# ============================================================

@router.get("/stats")
def get_document_stats(
    db: Session = Depends(
        get_db
    ),
):
    """
    Return overall document library statistics.

    Used by the Dashboard.

    Important:
    This route must be declared BEFORE the
    /{document_id} routes so that "stats" is
    not interpreted as a document ID.
    """

    try:

        # ----------------------------------------------------
        # Total documents
        # ----------------------------------------------------

        total_documents = (
            db.query(
                Document
            ).count()
        )

        # ----------------------------------------------------
        # Total logical pages
        # ----------------------------------------------------

        total_pages = sum(
            (
                document.page_count or 0
            )
            for document in (
                db.query(
                    Document
                ).all()
            )
        )

        # ----------------------------------------------------
        # Total chunks
        # ----------------------------------------------------

        total_chunks = (
            db.query(
                DocumentChunk
            ).count()
        )

        # ----------------------------------------------------
        # Response
        # ----------------------------------------------------

        return {
            "total_documents":
                total_documents,

            "total_pages":
                total_pages,

            "total_chunks":
                total_chunks,
        }

    except Exception as error:

        print(
            "GET DOCUMENT STATS ERROR:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not load document statistics. "
                "Please try again."
            ),
        )


# ============================================================
# GET DOCUMENT CHUNKS
# ============================================================

@router.get(
    "/{document_id}/chunks"
)
def get_document_chunks(
    document_id: int,

    db: Session = Depends(
        get_db
    ),
):
    """
    Return chunks and embedding status.
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

    try:

        chunks = (
            db.query(
                DocumentChunk
            )
            .filter(
                DocumentChunk.document_id
                == document_id
            )
            .order_by(
                DocumentChunk.chunk_index.asc()
            )
            .all()
        )

        return {
            "document_id":
                document.id,

            "filename":
                document.filename,

            "page_count":
                document.page_count or 0,

            "processing_status":
                get_processing_status(
                    document
                ),

            "chunk_count":
                len(chunks),

            "embedding_count":
                sum(
                    1
                    for chunk in chunks
                    if chunk.embedding
                ),

            "chunks": [
                {
                    "id":
                        chunk.id,

                    "chunk_index":
                        chunk.chunk_index,

                    "page_number":
                        chunk.page_number,

                    "content":
                        chunk.content,

                    "has_embedding":
                        bool(
                            chunk.embedding
                            and str(
                                chunk.embedding
                            ).strip()
                        ),
                }

                for chunk in chunks
            ],
        }

    except Exception as error:

        print(
            "GET DOCUMENT CHUNKS ERROR:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not load document chunks. "
                "Please try again."
            ),
        )


# ============================================================
# GET SINGLE DOCUMENT
# ============================================================

@router.get(
    "/{document_id}"
)
def get_document(
    document_id: int,

    db: Session = Depends(
        get_db
    ),
):
    """
    Return document metadata and extracted text.
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

    try:

        file_size = get_file_size(
            document.file_path
        )

        extension = get_file_extension(
            document.filename
        )

        chunk_count = len(
            document.chunks
        )

        embedding_count = sum(
            1
            for chunk in document.chunks
            if chunk.embedding
        )

        return {
            "id":
                document.id,

            "filename":
                document.filename,

            "page_count":
                document.page_count or 0,

            "text_length":
                document.text_length or 0,

            "chunk_count":
                chunk_count,

            "embedding_count":
                embedding_count,

            "uploaded_at":
                document.uploaded_at.isoformat(),

            "file_extension":
                extension,

            "file_size":
                file_size,

            "processing_status":
                get_processing_status(
                    document
                ),

            "file_available":
                bool(
                    document.file_path
                    and Path(
                        document.file_path
                    ).exists()
                ),

            "extracted_text":
                document.extracted_text
                or "",
        }

    except Exception as error:

        print(
            "GET DOCUMENT ERROR:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not load the document. "
                "Please try again."
            ),
        )


# ============================================================
# DOWNLOAD DOCUMENT
# ============================================================

@router.get(
    "/{document_id}/download"
)
def download_document(
    document_id: int,

    db: Session = Depends(
        get_db
    ),
):
    """
    Download the original document.

    If Keep uploaded files is OFF,
    the original file may no longer exist.
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

    if not document.file_path:

        raise HTTPException(
            status_code=404,
            detail=(
                "The original file is not available."
            ),
        )

    if not is_safe_upload_path(
        document.file_path
    ):

        raise HTTPException(
            status_code=500,
            detail=(
                "The stored file path is invalid."
            ),
        )

    file_path = Path(
        document.file_path
    )

    if not file_path.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "The original file is no longer "
                "available because uploaded file "
                "storage is disabled."
            ),
        )

    try:

        media_type = get_media_type(
            document.filename
        )

        return FileResponse(
            path=str(file_path),

            filename=document.filename,

            media_type=media_type,
        )

    except Exception as error:

        print(
            "DOWNLOAD DOCUMENT ERROR:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not download the document. "
                "Please try again."
            ),
        )


# ============================================================
# DELETE DOCUMENT
# ============================================================

@router.delete(
    "/{document_id}"
)
def delete_document(
    document_id: int,

    db: Session = Depends(
        get_db
    ),
):
    """
    Delete a document and its database records.
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

    filename = document.filename

    file_path = document.file_path

    # ========================================================
    # VERIFY STORED PATH
    # ========================================================

    if (
        file_path
        and not is_safe_upload_path(
            file_path
        )
    ):

        raise HTTPException(
            status_code=500,
            detail=(
                "The stored file path is invalid."
            ),
        )

    # ========================================================
    # DELETE DATABASE RECORD
    # ========================================================

    try:

        db.delete(
            document
        )

        db.commit()

    except Exception as error:

        db.rollback()

        print(
            "DELETE DOCUMENT DATABASE ERROR:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not delete the document "
                "from the database."
            ),
        )

    # ========================================================
    # DELETE PHYSICAL FILE
    # ========================================================

    file_deleted = delete_file_safely(
        file_path
    )

    # ========================================================
    # RESPONSE
    # ========================================================

    if file_deleted:

        message = (
            "Document and related chunks "
            "were deleted successfully."
        )

    else:

        message = (
            "The document record and related chunks "
            "were deleted, but the original file "
            "could not be removed."
        )

    return {
        "id":
            document_id,

        "filename":
            filename,

        "file_deleted":
            file_deleted,

        "message":
            message,
    }