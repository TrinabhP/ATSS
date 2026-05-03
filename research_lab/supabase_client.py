"""
supabase_client.py — Supabase write integration for the LabOS research pipeline.

This is the ONLY file in the Python backend that imports supabase.
All functions are synchronous.

Error handling contract:
  - get_client() raises EnvironmentError if env vars are missing (fail-fast).
  - save_analysis_results() and update_project_status() wrap Supabase calls in
    try/except, log the error, and return without raising — write failures must
    never abort the pipeline or propagate to callers.
  - Log messages NEVER include the SUPABASE_SERVICE_ROLE_KEY value.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from supabase import Client, create_client

logger = logging.getLogger(__name__)

# Module-level singleton — populated lazily by get_client()
_client: Optional[Client] = None


# ── Singleton ──────────────────────────────────────────────────────────────────


def get_client() -> Client:
    """
    Return the singleton Supabase Client, initialised lazily from env vars.

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


def save_analysis_results(
    project_id: str,
    user_id: str,
    results: Dict[str, Any],
) -> None:
    """
    Upsert a row in the analysis_results table with the full pipeline output.

    Uses ON CONFLICT on project_id (unique constraint) so repeated calls for the
    same project are idempotent.

    Logs and swallows any error — never raises.

    Args:
        project_id: UUID of the project this analysis belongs to.
        user_id:    UUID of the user who owns the project.
        results:    Pipeline output dict. Expected keys: literature, hypothesis,
                    procedure, final_recommendation, confidence_level,
                    action_items, caveats.
    """
    try:
        client = get_client()
        client.table("analysis_results").upsert(
            {
                "project_id": project_id,
                "user_id": user_id,
                "literature": results.get("literature"),
                "hypothesis": results.get("hypothesis"),
                "procedure": results.get("procedure"),
                "final_recommendation": results.get("final_recommendation"),
                "confidence_level": results.get("confidence_level"),
                "action_items": results.get("action_items", []),
                "caveats": results.get("caveats", []),
            },
            on_conflict="project_id",
        ).execute()
        logger.info(
            "Upserted analysis results for project=%s user=%s",
            project_id,
            user_id,
        )
    except Exception as exc:
        logger.error(
            "Failed to upsert analysis results for project=%s: %s",
            project_id,
            exc,
        )


def update_project_status(project_id: str, status: str) -> None:
    """
    Update the status column (and updated_at) on the projects table.

    Logs and swallows any error — never raises.

    Args:
        project_id: UUID of the project to update.
        status:     New status value, e.g. 'completed' or 'error'.
    """
    try:
        client = get_client()
        client.table("projects").update(
            {
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", project_id).execute()
        logger.info(
            "Updated project=%s status to '%s'",
            project_id,
            status,
        )
    except Exception as exc:
        logger.error(
            "Failed to update project=%s status to '%s': %s",
            project_id,
            status,
            exc,
        )
