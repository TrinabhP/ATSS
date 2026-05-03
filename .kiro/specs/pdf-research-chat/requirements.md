# Requirements Document

## Introduction

The PDF Research Chat feature adds a post-pipeline interactive chat capability to the LabOS Research Analysis Engine. After the multi-agent pipeline completes and produces a final PDF report, users can upload that PDF and start a conversational chat session with the Groq LLM (model: `openai/gpt-oss-20b`) using the PDF content as grounding context. This feature is backend-only — all new files, no modifications to existing code, no frontend changes.

## Glossary

- **Chat_Service**: The new backend module that manages PDF-grounded chat sessions, including PDF text extraction, session lifecycle, and LLM interaction via the Groq API.
- **PDF_Extractor**: The component within Chat_Service responsible for reading an uploaded PDF file and converting it to plain text.
- **Chat_Session**: An in-memory object that holds the extracted PDF text, conversation history (list of user/assistant message pairs), and a unique session identifier.
- **Groq_Client**: The Groq SDK client instance used to send chat completion requests to the `openai/gpt-oss-20b` model.
- **Conversation_History**: An ordered list of message dicts (`{"role": "user"|"assistant", "content": "..."}`) maintained per Chat_Session.
- **System_Prompt**: The initial instruction message sent to the LLM that includes the extracted PDF text as context and instructs the model to answer questions grounded in that content.
- **Chat_Router**: The new FastAPI APIRouter that exposes the PDF upload and chat endpoints, intended to be mounted on the existing FastAPI app.

## Requirements

### Requirement 1: PDF Upload and Text Extraction

**User Story:** As a researcher, I want to upload a PDF report from a completed pipeline run, so that I can use its content as context for an interactive chat session.

#### Acceptance Criteria

1. WHEN a PDF file is uploaded to the upload endpoint, THE PDF_Extractor SHALL extract all text content from the PDF and return it as a single string.
2. WHEN the uploaded PDF contains multiple pages, THE PDF_Extractor SHALL concatenate text from all pages in page order, separated by newline characters.
3. IF the uploaded file is not a valid PDF, THEN THE Chat_Service SHALL return an HTTP 400 error with a descriptive message indicating the file is not a valid PDF.
4. IF the uploaded PDF contains no extractable text (e.g., scanned image-only PDF), THEN THE Chat_Service SHALL return an HTTP 422 error with a message indicating no text could be extracted.
5. IF the extracted text exceeds 60,000 characters, THEN THE PDF_Extractor SHALL truncate the text to 60,000 characters and include a notice that the content was truncated.
6. WHEN text extraction succeeds, THE Chat_Service SHALL create a new Chat_Session with a unique session identifier and store the extracted text as the session context.
7. WHEN a Chat_Session is created, THE Chat_Service SHALL return the session identifier and a summary containing the character count and page count of the extracted PDF.

### Requirement 2: Chat Session Management

**User Story:** As a researcher, I want chat sessions to be tracked independently, so that I can have a dedicated conversation about a specific PDF report.

#### Acceptance Criteria

1. THE Chat_Service SHALL store Chat_Sessions in an in-memory dictionary keyed by session identifier.
2. WHEN a new Chat_Session is created, THE Chat_Service SHALL generate a UUID4 string as the session identifier.
3. WHEN a chat message request references a session identifier that does not exist, THE Chat_Service SHALL return an HTTP 404 error with a message indicating the session was not found.
4. WHEN a Chat_Session is created, THE Chat_Service SHALL initialize an empty Conversation_History list for that session.
5. WHEN a user sends a chat message, THE Chat_Service SHALL append the user message to the Conversation_History before sending the request to the LLM.
6. WHEN the LLM returns a response, THE Chat_Service SHALL append the assistant message to the Conversation_History.
7. THE Chat_Service SHALL expose an endpoint to list all active session identifiers with their creation timestamps and PDF summary metadata.
8. THE Chat_Service SHALL expose an endpoint to delete a specific Chat_Session by its session identifier, freeing the stored context and history.

### Requirement 3: Groq LLM Chat Interaction

**User Story:** As a researcher, I want to ask questions about my research PDF and receive answers grounded in the PDF content, so that I can explore findings interactively.

#### Acceptance Criteria

1. WHEN a chat message is sent for a valid Chat_Session, THE Chat_Service SHALL construct a message list containing: (a) a System_Prompt with the extracted PDF text as context, (b) the full Conversation_History, and (c) the new user message.
2. THE Chat_Service SHALL send the constructed message list to the Groq API using model `openai/gpt-oss-20b`.
3. THE Chat_Service SHALL use the existing `GROQ_API_KEY` environment variable to authenticate with the Groq API.
4. WHEN the Groq API returns a response, THE Chat_Service SHALL strip any `<think>...</think>` blocks from the response content before returning it to the caller.
5. WHEN the Groq API returns a response, THE Chat_Service SHALL return the cleaned assistant message along with the updated message count for the session.
6. IF the Groq API call fails, THEN THE Chat_Service SHALL return an HTTP 502 error with a message describing the upstream failure, without crashing the server.
7. IF the Groq API call times out after 60 seconds, THEN THE Chat_Service SHALL return an HTTP 504 error with a timeout message.
8. THE System_Prompt SHALL instruct the LLM to answer questions based on the provided PDF content and to indicate when a question falls outside the scope of the PDF.

### Requirement 4: Chat API Endpoint Design

**User Story:** As a developer, I want well-defined REST endpoints for the chat feature, so that the frontend team can integrate when ready.

#### Acceptance Criteria

1. THE Chat_Router SHALL expose `POST /api/chat/upload` accepting a multipart file upload and returning a session identifier with PDF metadata.
2. THE Chat_Router SHALL expose `POST /api/chat/{session_id}/message` accepting a JSON body with a `message` string field and returning the assistant response.
3. THE Chat_Router SHALL expose `GET /api/chat/sessions` returning a list of active sessions with their identifiers, creation timestamps, and PDF metadata.
4. THE Chat_Router SHALL expose `DELETE /api/chat/{session_id}` removing the specified session and returning a confirmation.
5. THE Chat_Router SHALL expose `GET /api/chat/{session_id}/history` returning the full Conversation_History for the specified session.
6. THE Chat_Router SHALL be implemented as a FastAPI `APIRouter` with prefix `/api/chat` so it can be mounted on the existing app without modifying `server.py`.
7. WHEN any endpoint receives a request body that fails validation, THE Chat_Router SHALL return an HTTP 422 error with field-level validation details.

### Requirement 5: New Files Only — No Existing Code Modifications

**User Story:** As a developer, I want the chat feature built entirely in new files, so that the existing pipeline and server remain untouched and stable.

#### Acceptance Criteria

1. THE Chat_Service SHALL be implemented entirely in new files under the `research_lab/` directory (e.g., `research_lab/chat/` subpackage).
2. THE Chat_Service SHALL NOT import from or modify `server.py`, `graph.py`, `state.py`, `literature.py`, `rag.py`, or any file under `agents/`.
3. THE Chat_Service SHALL NOT modify any files under the `labos-mockup/` directory.
4. THE Chat_Service SHALL include a `README` or integration guide documenting the exact steps needed to mount the Chat_Router on the existing FastAPI app.
5. THE Chat_Service SHALL only use dependencies already present in `requirements.txt` (groq, requests, python-dotenv) plus `PyPDF2` or `pdfplumber` for PDF extraction, which SHALL be documented as a new dependency to add.

### Requirement 6: Error Handling and Resilience

**User Story:** As a developer, I want robust error handling in the chat feature, so that failures in PDF parsing or LLM calls do not crash the server.

#### Acceptance Criteria

1. WHEN the PDF_Extractor encounters a corrupted or password-protected PDF, THE Chat_Service SHALL return an HTTP 400 error with a specific message describing the issue.
2. IF the `GROQ_API_KEY` environment variable is not set, THEN THE Chat_Service SHALL return an HTTP 503 error indicating the chat service is unavailable due to missing configuration.
3. WHEN any unexpected exception occurs during chat message processing, THE Chat_Service SHALL catch the exception, log it, and return an HTTP 500 error with a generic message without exposing internal details.
4. THE Chat_Service SHALL validate that uploaded files have a `.pdf` extension and a `application/pdf` content type before attempting extraction.
5. THE Chat_Service SHALL validate that chat message content is between 1 and 4,000 characters.
