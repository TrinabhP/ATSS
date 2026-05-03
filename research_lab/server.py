"""
server.py — FastAPI HTTP server for LabOS Research Analysis Engine.
Exposes POST /api/analyze which runs the full LangGraph pipeline
and returns the ResearchState as JSON.

Run with:
    python3 research_lab/server.py
"""

import os
import sys

# Allow imports from research_lab/ when run as `python3 research_lab/server.py`
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env from the repo root (one level up from research_lab/)
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env_path = os.path.join(_repo_root, ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _, _val = _line.partition("=")
                os.environ.setdefault(_key.strip(), _val.strip())

# Fix macOS Python SSL certificate issue — use certifi's CA bundle
# so that urllib (used by Biopython Entrez) can verify HTTPS connections.
try:
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
except ImportError:
    pass

from typing import Any, Dict, Optional, List
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
import uvicorn
import json
import asyncio

from graph import run_research, run_research_streaming

# ── Constants ──────────────────────────────────────────────────────────────────

MIN_ABSTRACT_LENGTH = 20
MAX_ABSTRACT_LENGTH = 4000

# ── App setup ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="LabOS Research Analysis Engine",
    description="Multi-agent research pipeline: Literature → Hypothesis → Procedure → Peer Review",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request / Response models ──────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    abstract: str

    @field_validator("abstract")
    @classmethod
    def validate_abstract(cls, v: str) -> str:
        v = v.strip()
        if len(v) < MIN_ABSTRACT_LENGTH:
            raise ValueError(f"Abstract must be at least {MIN_ABSTRACT_LENGTH} characters.")
        if len(v) > MAX_ABSTRACT_LENGTH:
            raise ValueError(f"Abstract must be at most {MAX_ABSTRACT_LENGTH} characters.")
        return v


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest) -> Dict[str, Any]:
    """
    Run the full research pipeline for the given abstract.
    Returns the complete ResearchState as a JSON object.
    """
    try:
        result = run_research(request.abstract)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # TypedDicts are already plain dicts — return directly
    return dict(result)


@app.post("/api/analyze/stream")
async def analyze_stream(request: AnalyzeRequest):
    """
    Run the pipeline and stream each agent's result as an SSE event.
    Events: literature, hypothesis, procedure, done
    """
    async def event_generator():
        try:
            for stage, state in run_research_streaming(request.abstract):
                # Build a JSON-safe snapshot of the current state
                payload = {
                    "stage": stage,
                    "literature": state.get("literature"),
                    "hypothesis": state.get("hypothesis"),
                    "procedure": state.get("procedure"),
                    "final_recommendation": state.get("final_recommendation"),
                    "confidence_level": state.get("confidence_level"),
                    "action_items": state.get("action_items", []),
                    "caveats": state.get("caveats", []),
                    "error": state.get("error"),
                    "current_stage": state.get("current_stage", ""),
                }
                data = json.dumps(payload, default=str)
                yield f"data: {data}\n\n"
                # Small yield to let the event loop flush
                await asyncio.sleep(0.01)
        except Exception as e:
            error_payload = json.dumps({"stage": "error", "error": str(e)})
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"LabOS API server starting on http://localhost:{port}")
    print(f"Frontend should connect to: http://localhost:{port}/api/analyze")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
