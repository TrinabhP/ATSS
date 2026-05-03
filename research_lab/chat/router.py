"""
chat/router.py — FastAPI APIRouter for PDF Research Chat.

Exposes 5 endpoints under /api/chat:
  POST   /api/chat/upload              — Upload PDF, create session
  POST   /api/chat/{session_id}/message — Send chat message
  GET    /api/chat/sessions            — List active sessions
  GET    /api/chat/{session_id}/history — Get conversation history
  DELETE /api/chat/{session_id}        — Delete session

Mount on the existing FastAPI app with:
    from chat import chat_router
    app.include_router(chat_router)

No imports from existing LabOS modules.
"""

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from . import chat_service
from .llm_client import get_chat_response, generate_chat_title
from .models import (
    ChatMessageRequest,
    ChatMessageResponse,
    ConversationMessage,
    DeleteResponse,
    HistoryResponse,
    SessionInfo,
    SessionListResponse,
    UploadResponse,
)
from .pdf_extractor import extract_text

logger = logging.getLogger("research_lab.chat")

chat_router = APIRouter(prefix="/api/chat", tags=["chat"])


# ── POST /api/chat/upload ──────────────────────────────────────────────────────


@chat_router.post("/upload", response_model=UploadResponse)
def upload_pdf(file: UploadFile = File(...)) -> UploadResponse:
    """Upload a PDF file and create a new chat session."""
    try:
        # Validate file extension and content type
        filename = file.filename or ""
        content_type = file.content_type or ""

        if not filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail="File must be a PDF (application/pdf).",
            )

        if content_type and content_type != "application/pdf":
            raise HTTPException(
                status_code=400,
                detail="File must be a PDF (application/pdf).",
            )

        # Read file bytes
        file_bytes = file.file.read()

        # Extract text
        try:
            extracted = extract_text(file_bytes)
        except ValueError as exc:
            # Distinguish "no text" (422) from other PDF errors (400)
            msg = str(exc)
            if "no extractable text" in msg.lower():
                raise HTTPException(status_code=422, detail=msg)
            raise HTTPException(status_code=400, detail=msg)

        # Create session
        session = chat_service.create_session(
            text=extracted.text,
            page_count=extracted.page_count,
            char_count=extracted.char_count,
            truncated=extracted.truncated,
        )

        return UploadResponse(
            session_id=session.session_id,
            page_count=session.page_count,
            char_count=session.char_count,
            truncated=session.truncated,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected error in upload: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")


# ── POST /api/chat/from-text ────────────────────────────────────────────────────


class CreateFromTextRequest(BaseModel):
    """Create a chat session from raw text (pipeline results)."""
    text: str
    name: str = ""


@chat_router.post("/from-text", response_model=UploadResponse)
def create_from_text(body: CreateFromTextRequest) -> UploadResponse:
    """Create a chat session directly from text content (no PDF upload needed)."""
    try:
        text = body.text.strip()
        if not text:
            raise HTTPException(status_code=422, detail="Text must not be empty.")

        # Truncate if needed
        from .pdf_extractor import MAX_TEXT_LENGTH
        truncated = len(text) > MAX_TEXT_LENGTH
        if truncated:
            text = text[:MAX_TEXT_LENGTH]

        session = chat_service.create_session(
            text=text,
            page_count=1,
            char_count=len(text),
            truncated=truncated,
        )
        if body.name:
            session.name = body.name

        return UploadResponse(
            session_id=session.session_id,
            page_count=1,
            char_count=len(text),
            truncated=truncated,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected error in create_from_text: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")


# ── POST /api/chat/export-pdf ──────────────────────────────────────────────────


class ExportPdfRequest(BaseModel):
    """Request body for server-side PDF generation."""
    title: str = "LabOS Research Plan"
    confidence_level: str = ""
    sections: list = []  # [{"heading": "...", "body": "..."}, ...]
    action_items: list = []
    caveats: list = []
    format: str = "standard"  # "standard" or "apa"


@chat_router.post("/export-pdf")
def export_pdf(body: ExportPdfRequest):
    """Generate a PDF server-side and return it as a downloadable file."""
    try:
        from .pdf_generator import generate_pdf
        pdf_bytes = generate_pdf(
            title=body.title,
            confidence_level=body.confidence_level,
            sections=body.sections,
            action_items=body.action_items,
            caveats=body.caveats,
            fmt=body.format,
        )
        filename = f"research-plan.pdf"
        return Response(
            content=bytes(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc:
        logger.error("PDF generation error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}")


# ── POST /api/chat/{session_id}/message ────────────────────────────────────────


@chat_router.post("/{session_id}/message", response_model=ChatMessageResponse)
def send_message(
    session_id: str,
    body: ChatMessageRequest,
) -> ChatMessageResponse:
    """Send a chat message and get an LLM response grounded in the PDF."""
    try:
        session = chat_service.get_session(session_id)
        if session is None:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found.",
            )

        # Append user message to history
        chat_service.append_user_message(session, body.message)

        # Build system prompt and get LLM response
        system_prompt = chat_service.build_system_prompt(session)

        try:
            response_text = get_chat_response(
                system_prompt=system_prompt,
                conversation_history=session.conversation_history,
            )
        except EnvironmentError:
            # Remove the user message we just appended since we can't process it
            if session.conversation_history:
                session.conversation_history.pop()
            raise HTTPException(
                status_code=503,
                detail="Chat service unavailable: LLM API key not configured.",
            )
        except TimeoutError:
            if session.conversation_history:
                session.conversation_history.pop()
            raise HTTPException(
                status_code=504,
                detail="LLM service timeout: request took too long.",
            )
        except RuntimeError:
            if session.conversation_history:
                session.conversation_history.pop()
            raise HTTPException(
                status_code=502,
                detail="LLM service error: unable to get response.",
            )

        # Append assistant response to history
        chat_service.append_assistant_message(session, response_text)

        # Auto-generate title after first user message
        if len(session.conversation_history) == 2 and not session.name:
            try:
                title = generate_chat_title(body.message)
                session.name = title
                logger.info("Auto-titled session %s: %s", session_id, title)
            except Exception:
                pass  # Non-critical — skip silently

        return ChatMessageResponse(
            response=response_text,
            message_count=len(session.conversation_history),
            session_name=session.name,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected error in send_message: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")


# ── GET /api/chat/sessions ─────────────────────────────────────────────────────


@chat_router.get("/sessions", response_model=SessionListResponse)
def list_sessions() -> SessionListResponse:
    """List all active chat sessions."""
    try:
        summaries = chat_service.list_sessions()
        return SessionListResponse(
            sessions=[
                SessionInfo(
                    session_id=s.session_id,
                    created_at=s.created_at,
                    page_count=s.page_count,
                    char_count=s.char_count,
                    truncated=s.truncated,
                    name=s.name,
                )
                for s in summaries
            ]
        )
    except Exception as exc:
        logger.error("Unexpected error in list_sessions: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")


# ── GET /api/chat/{session_id}/history ─────────────────────────────────────────


@chat_router.get("/{session_id}/history", response_model=HistoryResponse)
def get_history(session_id: str) -> HistoryResponse:
    """Get the full conversation history for a session."""
    try:
        session = chat_service.get_session(session_id)
        if session is None:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found.",
            )

        return HistoryResponse(
            session_id=session.session_id,
            messages=[
                ConversationMessage(role=m["role"], content=m["content"])
                for m in session.conversation_history
            ],
            message_count=len(session.conversation_history),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected error in get_history: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")


# ── PATCH /api/chat/{session_id}/rename ─────────────────────────────────────────


@chat_router.patch("/{session_id}/rename")
def rename_session_endpoint(session_id: str, body: dict):
    """Rename a chat session."""
    try:
        name = (body.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=422, detail="Name must not be empty.")
        ok = chat_service.rename_session(session_id, name)
        if not ok:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found.")
        return {"session_id": session_id, "name": name}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected error in rename: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")


# ── DELETE /api/chat/{session_id} ──────────────────────────────────────────────


@chat_router.delete("/{session_id}", response_model=DeleteResponse)
def delete_session(session_id: str) -> DeleteResponse:
    """Delete a chat session."""
    try:
        deleted = chat_service.delete_session(session_id)
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found.",
            )

        return DeleteResponse(deleted=True, session_id=session_id)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected error in delete_session: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")
