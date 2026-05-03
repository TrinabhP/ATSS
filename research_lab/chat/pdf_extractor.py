"""
chat/pdf_extractor.py — PDF text extraction using PyPDF2.

Reads an uploaded PDF file (as raw bytes), extracts text from all pages
in page order, and returns an ExtractedPDF dataclass. Truncates at
MAX_TEXT_LENGTH characters if the PDF is very large.

No imports from existing LabOS modules.
"""

import io
import logging
from dataclasses import dataclass

logger = logging.getLogger("research_lab.chat")

# ── Constants ──────────────────────────────────────────────────────────────────

MAX_TEXT_LENGTH: int = 60_000


# ── Data Structures ────────────────────────────────────────────────────────────


@dataclass
class ExtractedPDF:
    """Result of PDF text extraction."""

    text: str
    page_count: int
    char_count: int
    truncated: bool


# ── Public API ─────────────────────────────────────────────────────────────────


def extract_text(file_bytes: bytes) -> ExtractedPDF:
    """
    Extract all text from a PDF file.

    Args:
        file_bytes: Raw bytes of the uploaded PDF file.

    Returns:
        ExtractedPDF with concatenated text, page count, char count,
        and whether truncation occurred.

    Raises:
        ValueError: If the file is not a valid PDF, is password-protected,
                    or contains no extractable text.
    """
    try:
        from PyPDF2 import PdfReader
        from PyPDF2.errors import PdfReadError
    except ImportError:
        raise RuntimeError(
            "PyPDF2 is required for PDF extraction. "
            "Install with: pip install PyPDF2"
        )

    # Attempt to read the PDF
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
    except PdfReadError as exc:
        raise ValueError(f"Cannot read PDF: {exc}") from exc
    except Exception as exc:
        raise ValueError(
            "The uploaded file is not a valid PDF."
        ) from exc

    # Check for encryption / password protection
    if reader.is_encrypted:
        try:
            # Try empty password (some PDFs are "encrypted" with no password)
            if not reader.decrypt(""):
                raise ValueError(
                    "Cannot read PDF: the file is password-protected."
                )
        except Exception:
            raise ValueError(
                "Cannot read PDF: the file is password-protected."
            )

    # Extract text from all pages in order
    page_texts: list[str] = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        page_texts.append(text)

    page_count = len(page_texts)
    full_text = "\n".join(page_texts)

    # Check for empty extraction (image-only PDFs)
    if not full_text.strip():
        raise ValueError(
            "The PDF contains no extractable text (may be image-only)."
        )

    # Truncate if necessary
    truncated = False
    if len(full_text) > MAX_TEXT_LENGTH:
        full_text = full_text[:MAX_TEXT_LENGTH]
        truncated = True
        logger.info(
            "PDF text truncated from %d to %d characters",
            len("\n".join(page_texts)),
            MAX_TEXT_LENGTH,
        )

    char_count = len(full_text)

    return ExtractedPDF(
        text=full_text,
        page_count=page_count,
        char_count=char_count,
        truncated=truncated,
    )
