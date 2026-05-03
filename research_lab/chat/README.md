# PDF Research Chat — Integration Guide

## Overview

The `chat/` subpackage adds PDF-grounded conversational chat to the LabOS
Research Analysis Engine. After the pipeline produces a final report and the
user exports it as a PDF, they can upload that PDF here and ask questions
about it via the Groq LLM (`openai/gpt-oss-20b`).

## Setup

### 1. Install the new dependency

```bash
pip install PyPDF2 python-multipart
```

Or add to `requirements.txt`:

```
PyPDF2>=3.0.0
python-multipart>=0.0.6
```

### 2. Ensure `GROQ_API_KEY` is set

The chat feature uses the same `GROQ_API_KEY` environment variable that the
existing pipeline agents use. No new keys are needed.

### 3. Mount the router on the existing FastAPI app

Add **two lines** to `research_lab/server.py`:

```python
# At the top, with other imports:
from chat import chat_router

# After the existing app setup (after app.add_middleware(...)):
app.include_router(chat_router)
```

That's it. The server will now expose the chat endpoints alongside the
existing `/api/analyze` and `/health` routes.

## API Endpoints

All endpoints are prefixed with `/api/chat`.

### POST /api/chat/upload

Upload a PDF and create a new chat session.

**Request:** `multipart/form-data` with a `file` field containing the PDF.

**Response (200):**
```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "page_count": 3,
  "char_count": 12450,
  "truncated": false
}
```

**Errors:**
- `400` — File is not a valid PDF, wrong extension, corrupted, or password-protected
- `422` — PDF contains no extractable text (image-only)

---

### POST /api/chat/{session_id}/message

Send a message and get an LLM response grounded in the PDF.

**Request:**
```json
{
  "message": "What were the key findings about menin inhibitors?"
}
```

**Response (200):**
```json
{
  "response": "Based on the PDF, the key findings about menin inhibitors...",
  "message_count": 2
}
```

**Errors:**
- `404` — Session not found
- `502` — Groq API failure
- `503` — GROQ_API_KEY not configured
- `504` — Groq API timeout

---

### GET /api/chat/sessions

List all active chat sessions.

**Response (200):**
```json
{
  "sessions": [
    {
      "session_id": "a1b2c3d4-...",
      "created_at": "2025-05-02T12:00:00",
      "page_count": 3,
      "char_count": 12450,
      "truncated": false
    }
  ]
}
```

---

### GET /api/chat/{session_id}/history

Get the full conversation history for a session.

**Response (200):**
```json
{
  "session_id": "a1b2c3d4-...",
  "messages": [
    {"role": "user", "content": "What were the key findings?"},
    {"role": "assistant", "content": "Based on the PDF..."}
  ],
  "message_count": 2
}
```

**Errors:**
- `404` — Session not found

---

### DELETE /api/chat/{session_id}

Delete a chat session and free its memory.

**Response (200):**
```json
{
  "deleted": true,
  "session_id": "a1b2c3d4-..."
}
```

**Errors:**
- `404` — Session not found

## File Structure

```
research_lab/chat/
├── __init__.py          # Exports chat_router
├── models.py            # Pydantic models + dataclasses
├── pdf_extractor.py     # PDF → text (PyPDF2)
├── llm_client.py        # Groq API wrapper
├── chat_service.py      # In-memory session store
├── router.py            # FastAPI endpoints
└── README.md            # This file
```

## Architecture Notes

- **Zero modifications** to existing files — the chat module is fully self-contained
- **In-memory sessions** — sessions are lost on server restart (matches project constraint)
- **60,000 char limit** — PDF text is truncated to stay within Groq token limits
- **Synchronous** — no async/await, consistent with the rest of the codebase
- **Think-block stripping** — `<think>...</think>` blocks from the reasoning model are removed
