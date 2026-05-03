"""
chat/llm_client.py — Groq API wrapper for PDF Research Chat.

Mirrors the lazy-singleton pattern used in agents/orchestrator.py.
Strips <think>...</think> blocks from reasoning-model responses.

No imports from existing LabOS modules.
"""

import logging
import os
import re
from typing import Dict, List

logger = logging.getLogger("research_lab.chat")

# ── Constants ──────────────────────────────────────────────────────────────────

MODEL: str = "openai/gpt-oss-20b"
TIMEOUT: int = 60  # seconds
MAX_TOKENS: int = 4096

# ── Lazy singleton ─────────────────────────────────────────────────────────────

_client = None


def _get_client():
    """Return a cached Groq client, creating one on first call."""
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "Chat service unavailable: GROQ_API_KEY not configured."
            )
        from groq import Groq

        _client = Groq(api_key=api_key)
    return _client


# ── Helpers ────────────────────────────────────────────────────────────────────

_THINK_PATTERN = re.compile(r"<think>.*?</think>", flags=re.DOTALL)


def _strip_think_blocks(text: str) -> str:
    """Remove all <think>...</think> blocks from LLM output."""
    return _THINK_PATTERN.sub("", text).strip()


# ── Public API ─────────────────────────────────────────────────────────────────


def get_chat_response(
    system_prompt: str,
    conversation_history: List[Dict[str, str]],
) -> str:
    """
    Send a chat completion request to Groq.

    Args:
        system_prompt: System message containing PDF context.
        conversation_history: List of {"role": "user"|"assistant", "content": "..."}
                              dicts. The last entry should be the new user message.

    Returns:
        Cleaned assistant response text (think blocks stripped).

    Raises:
        EnvironmentError: If GROQ_API_KEY is not set.
        TimeoutError: If the Groq API does not respond within TIMEOUT seconds.
        RuntimeError: If the Groq API call fails for any other reason.
    """
    client = _get_client()  # may raise EnvironmentError

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_prompt},
    ]
    messages.extend(conversation_history)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=MAX_TOKENS,
            timeout=TIMEOUT,
        )
    except Exception as exc:
        exc_name = type(exc).__name__.lower()
        # Detect timeout-like exceptions from the Groq SDK / httpx
        if "timeout" in exc_name or "timed out" in str(exc).lower():
            logger.error("Groq API timeout: %s", exc)
            raise TimeoutError(
                "LLM service timeout: request took too long."
            ) from exc
        logger.error("Groq API error: %s", exc)
        raise RuntimeError(
            "LLM service error: unable to get response."
        ) from exc

    raw_text = response.choices[0].message.content or ""
    cleaned = _strip_think_blocks(raw_text)

    return cleaned


def generate_chat_title(user_message: str) -> str:
    """
    Generate a short title for a chat session based on the user's first message.

    Args:
        user_message: The user's initial chat message.

    Returns:
        A short title string (5-8 words).
    """
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Generate a very short title (5-8 words max) that summarizes "
                        "the user's research question below. Return ONLY the title text, "
                        "no quotes, no punctuation at the end, no explanation."
                    ),
                },
                {"role": "user", "content": user_message[:500]},
            ],
            max_tokens=30,
            timeout=15,
        )
        raw = response.choices[0].message.content or ""
        title = _strip_think_blocks(raw).strip().strip('"').strip("'")
        # Fallback if empty
        return title if title else user_message[:50]
    except Exception as exc:
        logger.warning("Failed to generate chat title: %s", exc)
        # Fallback: first 50 chars of the message
        return user_message[:50]
