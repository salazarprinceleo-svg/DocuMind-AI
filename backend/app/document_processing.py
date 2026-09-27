from pathlib import Path
from typing import Dict, List

from docx import Document as DocxDocument
from openpyxl import load_workbook
from pptx import Presentation
from pypdf import PdfReader


# ============================================================
# PDF EXTRACTION
# ============================================================

def extract_pdf_pages(
    file_path: str,
) -> List[Dict]:
    """
    Extract text from a PDF page by page.
    """

    reader = PdfReader(file_path)

    pages = []

    for index, page in enumerate(
        reader.pages,
        start=1,
    ):
        try:
            text = page.extract_text() or ""

        except Exception:
            text = ""

        pages.append(
            {
                "page_number": index,
                "text": text.strip(),
            }
        )

    return pages


# ============================================================
# DOCX EXTRACTION
# ============================================================

def extract_docx_pages(
    file_path: str,
) -> List[Dict]:
    """
    Extract text from a Word document.

    DOCX does not reliably expose physical page boundaries,
    so the document is treated as one logical page.

    Also extracts text from tables.
    """

    document = DocxDocument(file_path)

    parts = []

    # --------------------------------------------------------
    # Paragraphs
    # --------------------------------------------------------

    for paragraph in document.paragraphs:

        text = paragraph.text.strip()

        if text:
            parts.append(text)

    # --------------------------------------------------------
    # Tables
    # --------------------------------------------------------

    for table_index, table in enumerate(
        document.tables,
        start=1,
    ):
        parts.append(
            f"[Table {table_index}]"
        )

        for row in table.rows:

            cells = []

            for cell in row.cells:

                cell_text = cell.text.strip()

                cells.append(cell_text)

            row_text = " | ".join(cells)

            if row_text.strip():
                parts.append(row_text)

    combined_text = "\n".join(
        parts
    ).strip()

    if not combined_text:
        return []

    return [
        {
            "page_number": 1,
            "text": combined_text,
        }
    ]


# ============================================================
# EXCEL EXTRACTION
# ============================================================

def extract_xlsx_pages(
    file_path: str,
) -> List[Dict]:
    """
    Extract readable content from an Excel workbook.

    Each worksheet is treated as one logical page.

    Example output:

        [Sheet: Employees]

        Name | Position | Salary
        John | Manager | 25000
        Jane | Staff | 18000
    """

    workbook = load_workbook(
        filename=file_path,
        read_only=True,
        data_only=False,
    )

    pages = []

    for sheet_index, worksheet in enumerate(
        workbook.worksheets,
        start=1,
    ):

        lines = []

        lines.append(
            f"[Sheet: {worksheet.title}]"
        )

        for row in worksheet.iter_rows(
            values_only=True
        ):

            values = []

            for value in row:

                if value is None:
                    values.append("")

                else:
                    values.append(
                        str(value).strip()
                    )

            # Remove empty cells from the end
            while (
                values
                and values[-1] == ""
            ):
                values.pop()

            # Skip completely empty rows
            if not values:
                continue

            if not any(
                value.strip()
                for value in values
            ):
                continue

            lines.append(
                " | ".join(values)
            )

        sheet_text = "\n".join(
            lines
        ).strip()

        if sheet_text:
            pages.append(
                {
                    "page_number": sheet_index,
                    "text": sheet_text,
                }
            )

    workbook.close()

    return pages


# ============================================================
# POWERPOINT EXTRACTION
# ============================================================

def extract_pptx_pages(
    file_path: str,
) -> List[Dict]:
    """
    Extract readable text from a PowerPoint presentation.

    Each slide is treated as one logical page.

    Extracts:

        - Slide text
        - Titles
        - Bullets
        - Tables
        - Speaker notes when available
    """

    presentation = Presentation(
        file_path
    )

    pages = []

    for slide_index, slide in enumerate(
        presentation.slides,
        start=1,
    ):

        lines = []

        lines.append(
            f"[Slide {slide_index}]"
        )

        # ----------------------------------------------------
        # Slide shapes / text
        # ----------------------------------------------------

        for shape in slide.shapes:

            if hasattr(shape, "text"):

                text = shape.text.strip()

                if text:
                    lines.append(text)

            # ------------------------------------------------
            # Tables
            # ------------------------------------------------

            if getattr(
                shape,
                "has_table",
                False,
            ):

                table = shape.table

                lines.append(
                    "[Table]"
                )

                for row in table.rows:

                    cells = []

                    for cell in row.cells:

                        cell_text = (
                            cell.text.strip()
                        )

                        cells.append(
                            cell_text
                        )

                    row_text = (
                        " | ".join(cells)
                    )

                    if row_text.strip():
                        lines.append(
                            row_text
                        )

        # ----------------------------------------------------
        # Speaker notes
        # ----------------------------------------------------

        try:

            notes_slide = slide.notes_slide

            notes_text = []

            for shape in notes_slide.shapes:

                if hasattr(
                    shape,
                    "text",
                ):

                    text = (
                        shape.text.strip()
                    )

                    if text:
                        notes_text.append(
                            text
                        )

            if notes_text:

                lines.append(
                    "[Speaker Notes]"
                )

                lines.extend(
                    notes_text
                )

        except Exception:
            # Some PowerPoint files may not
            # expose speaker notes.
            pass

        slide_text = "\n".join(
            lines
        ).strip()

        if slide_text:

            pages.append(
                {
                    "page_number": slide_index,
                    "text": slide_text,
                }
            )

    return pages


# ============================================================
# TXT EXTRACTION
# ============================================================

def extract_txt_pages(
    file_path: str,
) -> List[Dict]:
    """
    Extract text from a plain text file.
    """

    encodings = [
        "utf-8",
        "utf-8-sig",
        "cp1252",
        "latin-1",
    ]

    text = ""

    for encoding in encodings:

        try:

            with open(
                file_path,
                "r",
                encoding=encoding,
            ) as file:

                text = file.read()

            break

        except UnicodeDecodeError:
            continue

    text = text.strip()

    if not text:
        return []

    return [
        {
            "page_number": 1,
            "text": text,
        }
    ]


# ============================================================
# GENERIC DOCUMENT EXTRACTION
# ============================================================

def extract_document_pages(
    file_path: str,
) -> List[Dict]:
    """
    Automatically select the correct extraction method.

    Supported formats:

        PDF
        DOCX
        XLSX
        PPTX
        TXT
    """

    extension = Path(
        file_path
    ).suffix.lower()

    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------

    if extension == ".pdf":

        return extract_pdf_pages(
            file_path
        )

    # --------------------------------------------------------
    # Word
    # --------------------------------------------------------

    if extension == ".docx":

        return extract_docx_pages(
            file_path
        )

    # --------------------------------------------------------
    # Excel
    # --------------------------------------------------------

    if extension == ".xlsx":

        return extract_xlsx_pages(
            file_path
        )

    # --------------------------------------------------------
    # PowerPoint
    # --------------------------------------------------------

    if extension == ".pptx":

        return extract_pptx_pages(
            file_path
        )

    # --------------------------------------------------------
    # Text
    # --------------------------------------------------------

    if extension == ".txt":

        return extract_txt_pages(
            file_path
        )

    raise ValueError(
        f"Unsupported file type: {extension}"
    )


# ============================================================
# COMBINE PAGE TEXT
# ============================================================

def combine_page_text(
    pages: List[Dict],
) -> str:
    """
    Combine extracted page text into one document string.
    """

    page_texts = []

    for page in pages:

        page_number = page.get(
            "page_number"
        )

        text = page.get(
            "text",
            "",
        ).strip()

        if not text:
            continue

        page_texts.append(
            f"[Page {page_number}]\n{text}"
        )

    return "\n\n".join(
        page_texts
    ).strip()