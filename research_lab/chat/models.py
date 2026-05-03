"""
chat/models.py — Pydantic request/response models and internal dataclasses
for the PDF Research Chat feature.

No imports from existing LabOS modules (state.py, agents/, etc.).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel, field_validator


# ── Pydantic Request Models ────────────────────────────────────────────────────


class ChatMessageRequest(BaseModel):
    """Request body for POST /api/chat/{session_id}/message"""

    message: str

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 1:
            raise ValueError("Message must not be empty.")
        if len(v) > 4000:
            raise ValueError("Message must be at most 4,000 characters.")
        return v


# ── Pydantic Response Models ───────────────────────────────────────────────────


class UploadResponse(BaseModel):
    """Response for POST /api/chat/upload"""

    session_id: str
    page_count: int
    char_count: int
    truncated: bool


class ChatMessageResponse(BaseModel):
    """Response for POST /api/chat/{session_id}/message"""

    response: str
    message_count: int
    session_name: str = ""


class SessionInfo(BaseModel):
    """Single session entry in the sessions list"""

    session_id: str
    created_at: str  # ISO 8601 timestamp
    page_count: int
    char_count: int
    truncated: bool
    name: str = ""


class SessionListResponse(BaseModel):
    """Response for GET /api/chat/sessions"""

    sessions: List[SessionInfo]


class ConversationMessage(BaseModel):
    """Single message in conversation history"""

    role: str  # "user" or "assistant"
    content: str


class HistoryResponse(BaseModel):
    """Response for GET /api/chat/{session_id}/history"""

    session_id: str
    messages: List[ConversationMessage]
    message_count: int


class DeleteResponse(BaseModel):
    """Response for DELETE /api/chat/{session_id}"""

    deleted: bool
    session_id: str


class ErrorResponse(BaseModel):
    """Standard error response body"""

    detail: str


# ── Internal Data Structures ───────────────────────────────────────────────────


@dataclass
class ChatSession:
    """In-memory chat session object."""

    session_id: str  # UUID4 string
    pdf_text: str  # Extracted PDF content
    page_count: int  # Number of pages in source PDF
    char_count: int  # Character count of extracted text
    truncated: bool  # Whether text was truncated at 60k chars
    created_at: datetime  # Session creation timestamp
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    # Each entry: {"role": "user"|"assistant", "content": "..."}
    name: str = ""  # Auto-generated or user-set session name


@dataclass
class SessionSummary:
    """Lightweight session metadata for listing."""

    session_id: str
    created_at: str  # ISO 8601
    page_count: int
    char_count: int
    truncated: bool
    name: str = ""
