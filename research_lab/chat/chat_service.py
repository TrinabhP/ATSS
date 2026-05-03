"""
chat/chat_service.py — In-memory session management for PDF Research Chat.

Stores chat sessions in a plain dict keyed by UUID4 session IDs.
No database, no persistence — matches the project's in-memory-only constraint.

No imports from existing LabOS modules.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from .models import ChatSession, SessionSummary

logger = logging.getLogger("research_lab.chat")

# ── In-memory store ────────────────────────────────────────────────────────────

_sessions: Dict[str, ChatSession] = {}

# ── System prompt template ─────────────────────────────────────────────────────

SYSTEM_PROMPT_TEMPLATE = """You are a research assistant helping a scientist analyze a PDF research document.
Answer questions based ONLY on the content of the provided PDF document below.

If a question asks about something not covered in the PDF, clearly state that the information is not available in the provided document.

Be precise, cite specific sections or findings from the document when possible, and maintain a scientific tone.

--- PDF CONTENT START ---
{pdf_text}
--- PDF CONTENT END ---

{truncation_notice}"""

TRUNCATION_NOTICE = (
    "Note: The PDF content was truncated to fit context limits. "
    "Some content from later pages may be missing."
)


# ── Public API ─────────────────────────────────────────────────────────────────


def create_session(
    text: str,
    page_count: int,
    char_count: int,
    truncated: bool,
) -> ChatSession:
    """Create a new chat session with extracted PDF context."""
    session_id = str(uuid.uuid4())
    session = ChatSession(
        session_id=session_id,
        pdf_text=text,
        page_count=page_count,
        char_count=char_count,
        truncated=truncated,
        created_at=datetime.utcnow(),
        conversation_history=[],
    )
    _sessions[session_id] = session
    logger.info("Created chat session %s (%d chars, %d pages)", session_id, char_count, page_count)
    return session


def get_session(session_id: str) -> Optional[ChatSession]:
    """Retrieve a session by ID. Returns None if not found."""
    return _sessions.get(session_id)


def delete_session(session_id: str) -> bool:
    """Delete a session. Returns True if deleted, False if not found."""
    if session_id in _sessions:
        del _sessions[session_id]
        logger.info("Deleted chat session %s", session_id)
        return True
    return False


def list_sessions() -> List[SessionSummary]:
    """Return summary metadata for all active sessions."""
    summaries: List[SessionSummary] = []
    for session in _sessions.values():
        summaries.append(
            SessionSummary(
                session_id=session.session_id,
                created_at=session.created_at.isoformat(),
                page_count=session.page_count,
                char_count=session.char_count,
                truncated=session.truncated,
                name=session.name,
            )
        )
    return summaries


def append_user_message(session: ChatSession, content: str) -> None:
    """Append a user message to the session's conversation history."""
    session.conversation_history.append({"role": "user", "content": content})


def append_assistant_message(session: ChatSession, content: str) -> None:
    """Append an assistant message to the session's conversation history."""
    session.conversation_history.append({"role": "assistant", "content": content})


def build_system_prompt(session: ChatSession) -> str:
    """Build the system prompt containing PDF context and instructions."""
    notice = TRUNCATION_NOTICE if session.truncated else ""
    return SYSTEM_PROMPT_TEMPLATE.format(
        pdf_text=session.pdf_text,
        truncation_notice=notice,
    )


def rename_session(session_id: str, name: str) -> bool:
    """Rename a session. Returns True if renamed, False if not found."""
    session = _sessions.get(session_id)
    if session is None:
        return False
    session.name = name
    return True


def clear_all_sessions() -> None:
    """Remove all sessions. Useful for testing."""
    _sessions.clear()
