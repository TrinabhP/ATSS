# Implementation Plan: PDF Research Chat

## Overview

Build a self-contained `research_lab/chat/` subpackage that adds PDF-grounded conversational chat to the LabOS Research Analysis Engine. All code lives in new files — zero modifications to existing code. The implementation proceeds bottom-up: data models → PDF extraction → LLM client → session service → router → integration guide, with property-based and unit tests woven in alongside each component.

## Tasks

- [ ] 1. Set up the chat subpackage structure and data models
  - [ ] 1.1 Create `research_lab/chat/` directory with `__init__.py`, exporting `chat_router` (placeholder import initially)
    - Create `research_lab/chat/__init__.py`
    - _Requirements: 5.1, 4.6_
  - [ ] 1.2 Create `research_lab/chat/models.py` with all Pydantic request/response models and internal dataclasses
    - Define `ChatMessageRequest` with `message` field validator (1–4,000 chars after strip)
    - Define `UploadResponse`, `ChatMessageResponse`, `SessionInfo`, `SessionListResponse`, `ConversationMessage`, `HistoryResponse`, `DeleteResponse`, `ErrorResponse`
    - Define `ChatSession` dataclass (session_id, pdf_text, page_count, char_count, truncated, created_at, conversation_history)
    - Define `SessionSummary` dataclass
    - _Requirements: 2.1, 2.4, 4.1, 4.2, 4.3, 4.4, 4.5, 6.5_
  - [ ]* 1.3 Write property test for message length validation (Property 10)
    - **Property 10: Message length validation**
    - Use Hypothesis `st.text()` to generate strings of varying lengths
    - Verify `ChatMessageRequest` accepts stripped strings between 1–4,000 chars and rejects empty or >4,000 char strings
    - Test file: `research_lab/tests/test_chat/test_models.py`
    - **Validates: Requirements 6.5**

- [ ] 2. Implement PDF text extraction
  - [ ] 2.1 Create `research_lab/chat/pdf_extractor.py`
    - Define `ExtractedPDF` dataclass with `text`, `page_count`, `char_count`, `truncated` fields
    - Define `MAX_TEXT_LENGTH = 60_000` constant
    - Implement `extract_text(file_bytes: bytes) -> ExtractedPDF`
    - Use PyPDF2 `PdfReader` to read pages, concatenate text with newline separators in page order
    - Truncate to 60,000 chars if exceeded, set `truncated=True`
    - Raise `ValueError` for invalid PDFs, password-protected PDFs, and PDFs with no extractable text
    - Add `PyPDF2` to `requirements.txt` as a new dependency
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 5.5, 6.1_
  - [ ]* 2.2 Write property test for PDF text extraction page order (Property 1)
    - **Property 1: PDF text extraction preserves page-ordered content**
    - Use `fpdf2` to generate multi-page PDFs with known text per page in the test
    - Extract and verify text from page i appears before text from page i+1
    - Test file: `research_lab/tests/test_chat/test_pdf_extractor.py`
    - **Validates: Requirements 1.1, 1.2**
  - [ ]* 2.3 Write property test for invalid bytes rejection (Property 2)
    - **Property 2: Invalid bytes are rejected**
    - Use Hypothesis `st.binary()` to generate random byte sequences
    - Verify `extract_text` raises `ValueError` for non-PDF bytes
    - Test file: `research_lab/tests/test_chat/test_pdf_extractor.py`
    - **Validates: Requirements 1.3**
  - [ ]* 2.4 Write property test for text truncation at 60k chars (Property 3)
    - **Property 3: Text truncation at 60,000 characters**
    - Generate PDFs with text exceeding 60,000 chars using `fpdf2`
    - Verify `truncated=True` and `len(text) == 60_000` when exceeded
    - Verify `truncated=False` and full text returned when ≤ 60,000 chars
    - Test file: `research_lab/tests/test_chat/test_pdf_extractor.py`
    - **Validates: Requirements 1.5**

- [ ] 3. Checkpoint — Verify models and PDF extraction
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Implement the Groq LLM client
  - [ ] 4.1 Create `research_lab/chat/llm_client.py`
    - Define `MODEL = "openai/gpt-oss-20b"` and `TIMEOUT = 60` constants
    - Implement lazy singleton Groq client pattern (matching `orchestrator.py` style)
    - Implement `_strip_think_blocks(text: str) -> str` using `re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)`
    - Implement `get_chat_response(system_prompt: str, conversation_history: List[Dict[str, str]]) -> str`
    - Raise `EnvironmentError` if `GROQ_API_KEY` not set
    - Raise `TimeoutError` on Groq API timeout (>60s)
    - Raise `RuntimeError` on other Groq API failures
    - Return cleaned response text with think blocks stripped
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_
  - [ ]* 4.2 Write property test for think block stripping (Property 8)
    - **Property 8: Think block stripping**
    - Use Hypothesis to generate strings with embedded `<think>...</think>` blocks
    - Verify all think blocks are removed and all non-think content is preserved
    - Test file: `research_lab/tests/test_chat/test_llm_client.py`
    - **Validates: Requirements 3.4**

- [ ] 5. Implement chat session management service
  - [ ] 5.1 Create `research_lab/chat/chat_service.py`
    - Implement in-memory `_sessions: Dict[str, ChatSession]` store
    - Implement `create_session(text, page_count, char_count, truncated) -> ChatSession` — generates UUID4, stores session
    - Implement `get_session(session_id) -> Optional[ChatSession]`
    - Implement `delete_session(session_id) -> bool`
    - Implement `list_sessions() -> List[SessionSummary]`
    - Implement `append_user_message(session, content)` and `append_assistant_message(session, content)`
    - Implement `build_system_prompt(session) -> str` using the system prompt template with PDF text and truncation notice
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 3.1, 3.8_
  - [ ]* 5.2 Write property test for session creation invariants (Property 4)
    - **Property 4: Session creation invariants**
    - Use Hypothesis to generate random text, page_count, char_count, truncated values
    - Verify session_id is valid UUID4, pdf_text matches input, metadata matches, conversation_history is empty
    - Test file: `research_lab/tests/test_chat/test_chat_service.py`
    - **Validates: Requirements 1.6, 1.7, 2.2, 2.4**
  - [ ]* 5.3 Write property test for conversation history ordering (Property 5)
    - **Property 5: Conversation history preserves message order and roles**
    - Generate sequences of N user/assistant message pairs, append alternately
    - Verify 2N entries, correct role alternation, content matches
    - Test file: `research_lab/tests/test_chat/test_chat_service.py`
    - **Validates: Requirements 2.5, 2.6**
  - [ ]* 5.4 Write property test for session deletion (Property 6)
    - **Property 6: Session deletion makes session unretrievable**
    - Create session, delete it, verify `get_session` returns `None`
    - Test file: `research_lab/tests/test_chat/test_chat_service.py`
    - **Validates: Requirements 2.8**
  - [ ]* 5.5 Write property test for message list construction (Property 7)
    - **Property 7: Message list construction includes system prompt, history, and new message**
    - Generate sessions with varying history lengths and new user messages
    - Verify list length is K+2, first message is system with PDF text, middle K match history, last is new user message
    - Test file: `research_lab/tests/test_chat/test_chat_service.py`
    - **Validates: Requirements 3.1**

- [ ] 6. Checkpoint — Verify LLM client and session service
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Implement the FastAPI router with all endpoints
  - [ ] 7.1 Create `research_lab/chat/router.py` with all 5 endpoints
    - Create `chat_router = APIRouter(prefix="/api/chat", tags=["chat"])`
    - Implement `POST /api/chat/upload` — accept multipart file, validate `.pdf` extension and `application/pdf` content type, call `extract_text`, call `create_session`, return `UploadResponse`
    - Implement `POST /api/chat/{session_id}/message` — validate session exists (404 if not), append user message, call `get_chat_response` with built system prompt and history, append assistant response, return `ChatMessageResponse`
    - Implement `GET /api/chat/sessions` — call `list_sessions`, return `SessionListResponse`
    - Implement `GET /api/chat/{session_id}/history` — validate session exists (404 if not), return `HistoryResponse`
    - Implement `DELETE /api/chat/{session_id}` — call `delete_session`, return `DeleteResponse` (404 if not found)
    - Map exceptions: `ValueError` → 400/422, `EnvironmentError` → 503, `TimeoutError` → 504, `RuntimeError` → 502, `Exception` → 500
    - Add logging using `logging.getLogger("research_lab.chat")`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 6.1, 6.2, 6.3, 6.4, 6.5_
  - [ ] 7.2 Update `research_lab/chat/__init__.py` to export `chat_router` from `router.py`
    - Replace placeholder with `from .router import chat_router`
    - _Requirements: 4.6, 5.1_
  - [ ]* 7.3 Write property test for file upload validation (Property 9)
    - **Property 9: File upload validation rejects non-PDF files**
    - Use Hypothesis to generate filenames with various extensions
    - Verify only `.pdf` files with `application/pdf` content type are accepted; all others get HTTP 400
    - Test file: `research_lab/tests/test_chat/test_router.py`
    - **Validates: Requirements 6.4**
  - [ ]* 7.4 Write unit tests for router error handling
    - Test non-existent session returns 404
    - Test Groq API failure returns 502 (mock `get_chat_response` to raise `RuntimeError`)
    - Test Groq API timeout returns 504 (mock to raise `TimeoutError`)
    - Test missing `GROQ_API_KEY` returns 503 (mock to raise `EnvironmentError`)
    - Test corrupted PDF returns 400
    - Test validation error returns 422
    - Use `fastapi.testclient.TestClient` and `unittest.mock`
    - Test file: `research_lab/tests/test_chat/test_router.py`
    - _Requirements: 2.3, 3.6, 3.7, 6.1, 6.2, 6.3, 6.4_

- [ ] 8. Checkpoint — Verify router and all endpoints
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Create integration guide and wire everything together
  - [ ] 9.1 Create `research_lab/chat/README.md` with integration instructions
    - Document the two lines needed to mount the router in `server.py`: `from chat import chat_router` and `app.include_router(chat_router)`
    - Document the `PyPDF2` dependency addition to `requirements.txt`
    - Document the `GROQ_API_KEY` environment variable requirement
    - List all 5 endpoints with request/response examples
    - _Requirements: 5.4, 5.5_
  - [ ]* 9.2 Write integration tests for the full upload → chat → history → delete flow
    - Test complete lifecycle: upload PDF → send message (mocked LLM) → get history → list sessions → delete session → verify 404
    - Test multiple concurrent sessions are independent
    - Use `fastapi.testclient.TestClient` with mocked Groq API
    - Test file: `research_lab/tests/test_chat/test_integration.py`
    - _Requirements: 1.1, 1.6, 2.1, 2.5, 2.7, 2.8, 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 10. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation after each major component
- Property tests validate the 10 universal correctness properties from the design document using Hypothesis
- Unit tests validate specific examples, edge cases, and error handling
- All code is Python 3.11+, synchronous (no async/await in business logic), with type hints throughout
- Test dependencies needed: `pytest`, `hypothesis`, `fpdf2` (for generating test PDFs), `httpx` (for TestClient)
