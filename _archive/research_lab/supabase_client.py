"""
supabase_client.py — Supabase write integration for the LabOS research pipeline.

This is the ONLY file in the Python codebase that imports supabase.
All functions are synchronous — no async/await.

Error handling contract:
  - get_client() raises EnvironmentError if env vars are missing (fail-fast at startup).
  - All other public functions wrap their Supabase calls in try/except, log the error,
    and return without raising — Supabase write failures must never abort the pipeline.
  - Log messages NEVER include the SUPABASE_SERVICE_ROLE_KEY value.
"""

import logging
import os
from typing import Optional

from supabase import Client, create_client

from research_lab.state import CriticReview

logger = logging.getLogger(__name__)

# Module-level singleton — populated lazily by get_client()
_client: Optional[Client] = None


# ── Singleton ──────────────────────────────────────────────────────────────────

def get_client() -> Client:
    """
    Return the singleton supabase-py Client, initialised lazily from env vars.

    Raises:
        EnvironmentError: if SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is not set.
    """
    global _client
    if _client is not None:
        return _client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url:
        raise EnvironmentError(
            "SUPABASE_URL environment variable is not set. "
            "Set it to your Supabase project URL before running the pipeline."
        )
    if not key:
        raise EnvironmentError(
            "SUPABASE_SERVICE_ROLE_KEY environment variable is not set. "
            "Set it to your Supabase service role key before running the pipeline."
        )

    logger.info("Initialising Supabase client for URL: %s", url)
    _client = create_client(url, key)
    return _client


# ── Public write functions ─────────────────────────────────────────────────────

def create_session(abstract: str) -> str:
    """
    Insert a research_sessions row with status='running'.

    Returns:
        The new session UUID as a string.

    Raises:
        Exception: propagates on failure — caller (graph.py) is responsible for
                   catching and deciding whether to continue without persistence.
    """
    client = get_client()
    response = (
        client.table("research_sessions")
        .insert({"abstract": abstract, "status": "running"})
        .execute()
    )
    session_id: str = response.data[0]["id"]
    logger.info("Created research session: %s", session_id)
    return session_id


def upsert_agent_output(
    session_id: str,
    agent_name: str,
    revision_count: int,
    output: dict,
) -> None:
    """
    Upsert a row in agent_outputs.

    Uses ON CONFLICT (session_id, agent_name) DO UPDATE so retries are idempotent.
    Logs and swallows any Supabase error — never raises.

    Args:
        session_id:     UUID of the parent research session.
        agent_name:     One of 'literature', 'hypothesis', 'procedure'.
        revision_count: How many revisions this agent went through.
        output:         The agent's full output dict (must be JSON-serialisable).
    """
    try:
        client = get_client()
        client.table("agent_outputs").upsert(
            {
                "session_id": session_id,
                "agent_name": agent_name,
                "revision_count": revision_count,
                "output_json": output,
            },
            on_conflict="session_id,agent_name",
        ).execute()
        logger.info(
            "Upserted agent output for session=%s agent=%s revision=%d",
            session_id,
            agent_name,
            revision_count,
        )
    except Exception as exc:
        logger.error(
            "Failed to upsert agent output for session=%s agent=%s: %s",
            session_id,
            agent_name,
            exc,
        )


def insert_critic_review(session_id: str, review: CriticReview) -> None:
    """
    Insert a row in critic_reviews.

    Logs and swallows any Supabase error — never raises.

    Args:
        session_id: UUID of the parent research session.
        review:     CriticReview TypedDict with keys: agent_name, revision_number,
                    passed, feedback, timestamp (stored as reviewed_at).
    """
    try:
        client = get_client()
        client.table("critic_reviews").insert(
            {
                "session_id": session_id,
                "agent_name": review["agent_name"],
                "revision_number": review["revision_number"],
                "passed": review["passed"],
                "feedback": review.get("feedback", ""),
                "reviewed_at": review["timestamp"],
            }
        ).execute()
        logger.info(
            "Inserted critic review for session=%s agent=%s revision=%d passed=%s",
            session_id,
            review["agent_name"],
            review["revision_number"],
            review["passed"],
        )
    except Exception as exc:
        logger.error(
            "Failed to insert critic review for session=%s agent=%s: %s",
            session_id,
            review.get("agent_name", "unknown"),
            exc,
        )


def insert_final_synthesis(
    session_id: str,
    final_recommendation: str,
    confidence_level: str,
    action_items: list,
    caveats: list,
) -> None:
    """
    Insert a row in final_syntheses and update research_sessions.status to 'complete'.

    Logs and swallows any Supabase error — never raises.

    Args:
        session_id:           UUID of the parent research session.
        final_recommendation: The synthesised recommendation text.
        confidence_level:     One of 'High', 'Moderate', 'Low'.
        action_items:         List of action item strings.
        caveats:              List of caveat strings.
    """
    try:
        client = get_client()
        client.table("final_syntheses").insert(
            {
                "session_id": session_id,
                "final_recommendation": final_recommendation,
                "confidence_level": confidence_level,
                "action_items": action_items,
                "caveats": caveats,
            }
        ).execute()
        logger.info("Inserted final synthesis for session=%s", session_id)

        client.table("research_sessions").update({"status": "complete"}).eq(
            "id", session_id
        ).execute()
        logger.info("Marked session=%s as complete", session_id)
    except Exception as exc:
        logger.error(
            "Failed to insert final synthesis for session=%s: %s",
            session_id,
            exc,
        )


def mark_session_error(session_id: str, error_message: str) -> None:
    """
    Update research_sessions SET status='error', error=error_message.

    Logs and swallows any Supabase error — never raises.

    Args:
        session_id:    UUID of the research session to mark as errored.
        error_message: Human-readable description of what went wrong.
    """
    try:
        client = get_client()
        client.table("research_sessions").update(
            {"status": "error", "error": error_message}
        ).eq("id", session_id).execute()
        logger.info(
            "Marked session=%s as error: %s", session_id, error_message
        )
    except Exception as exc:
        logger.error(
            "Failed to mark session=%s as error: %s",
            session_id,
            exc,
        )
