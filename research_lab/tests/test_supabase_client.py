"""
test_supabase_client.py — Unit tests for research_lab/supabase_client.py

Tests cover:
  - create_session returns a UUID string
  - upsert_agent_output swallows exceptions
  - insert_critic_review swallows exceptions
  - mark_session_error swallows exceptions
  - get_client raises EnvironmentError when env vars are missing
  - log output never contains the SUPABASE_SERVICE_ROLE_KEY value

Requirements: 2.7, 2.8, 2.9
"""

import logging
import uuid
from unittest.mock import MagicMock, patch

import pytest

import research_lab.supabase_client as sc


# ── Helpers ────────────────────────────────────────────────────────────────────

FAKE_SESSION_ID = str(uuid.uuid4())
FAKE_URL = "https://fake.supabase.co"
FAKE_KEY = "super-secret-service-role-key-value"


def _make_mock_client(session_id: str = FAKE_SESSION_ID) -> MagicMock:
    """Return a mock supabase Client whose table().insert/upsert/update chains work."""
    mock_client = MagicMock()

    # Fluent chain: .table(...).insert(...).execute() → response with data
    insert_response = MagicMock()
    insert_response.data = [{"id": session_id}]

    chain = MagicMock()
    chain.execute.return_value = insert_response
    chain.upsert.return_value = chain
    chain.insert.return_value = chain
    chain.update.return_value = chain
    chain.eq.return_value = chain

    mock_client.table.return_value = chain
    return mock_client


# ── Tests ──────────────────────────────────────────────────────────────────────


class TestCreateSession:
    def test_create_session_returns_uuid(self, monkeypatch):
        """create_session() should return the UUID string from the insert response."""
        expected_id = str(uuid.uuid4())
        mock_client = _make_mock_client(session_id=expected_id)

        # Reset singleton and inject mock
        monkeypatch.setattr(sc, "_client", mock_client)

        result = sc.create_session("some abstract text")

        assert result == expected_id
        assert isinstance(result, str)
        # Verify the correct table was targeted
        mock_client.table.assert_called_with("research_sessions")


class TestUpsertAgentOutput:
    def test_upsert_agent_output_swallows_error(self, monkeypatch):
        """upsert_agent_output() must not raise even when the client raises."""
        mock_client = MagicMock()
        mock_client.table.return_value.upsert.return_value.execute.side_effect = (
            RuntimeError("Supabase network error")
        )

        monkeypatch.setattr(sc, "_client", mock_client)

        # Should not raise
        sc.upsert_agent_output(
            session_id=FAKE_SESSION_ID,
            agent_name="literature",
            revision_count=1,
            output={"key": "value"},
        )

    def test_upsert_agent_output_calls_correct_table(self, monkeypatch):
        """upsert_agent_output() should target the agent_outputs table."""
        mock_client = _make_mock_client()
        monkeypatch.setattr(sc, "_client", mock_client)

        sc.upsert_agent_output(
            session_id=FAKE_SESSION_ID,
            agent_name="hypothesis",
            revision_count=0,
            output={"hypothesis": "test"},
        )

        mock_client.table.assert_called_with("agent_outputs")


class TestInsertCriticReview:
    def test_insert_critic_review_swallows_error(self, monkeypatch):
        """insert_critic_review() must not raise even when the client raises."""
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.side_effect = (
            ConnectionError("timeout")
        )

        monkeypatch.setattr(sc, "_client", mock_client)

        review = {
            "agent_name": "literature",
            "revision_number": 0,
            "passed": True,
            "feedback": "",
            "timestamp": "2024-01-01T00:00:00Z",
        }

        # Should not raise
        sc.insert_critic_review(session_id=FAKE_SESSION_ID, review=review)

    def test_insert_critic_review_calls_correct_table(self, monkeypatch):
        """insert_critic_review() should target the critic_reviews table."""
        mock_client = _make_mock_client()
        monkeypatch.setattr(sc, "_client", mock_client)

        review = {
            "agent_name": "hypothesis",
            "revision_number": 1,
            "passed": False,
            "feedback": "Needs more detail",
            "timestamp": "2024-06-01T12:00:00Z",
        }

        sc.insert_critic_review(session_id=FAKE_SESSION_ID, review=review)

        mock_client.table.assert_called_with("critic_reviews")


class TestMarkSessionError:
    def test_mark_session_error_swallows_error(self, monkeypatch):
        """mark_session_error() must not raise even when the client raises."""
        mock_client = MagicMock()
        mock_client.table.return_value.update.return_value.eq.return_value.execute.side_effect = (
            ValueError("unexpected error")
        )

        monkeypatch.setattr(sc, "_client", mock_client)

        # Should not raise
        sc.mark_session_error(
            session_id=FAKE_SESSION_ID,
            error_message="Pipeline failed at hypothesis stage",
        )

    def test_mark_session_error_calls_correct_table(self, monkeypatch):
        """mark_session_error() should target the research_sessions table."""
        mock_client = _make_mock_client()
        monkeypatch.setattr(sc, "_client", mock_client)

        sc.mark_session_error(
            session_id=FAKE_SESSION_ID,
            error_message="Something went wrong",
        )

        mock_client.table.assert_called_with("research_sessions")


class TestGetClient:
    def test_get_client_raises_on_missing_env(self, monkeypatch):
        """get_client() must raise EnvironmentError when env vars are absent."""
        # Reset singleton so get_client() actually tries to initialise
        monkeypatch.setattr(sc, "_client", None)
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

        with pytest.raises(EnvironmentError):
            sc.get_client()

    def test_get_client_raises_on_missing_url(self, monkeypatch):
        """get_client() must raise EnvironmentError when only SUPABASE_URL is missing."""
        monkeypatch.setattr(sc, "_client", None)
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", FAKE_KEY)

        with pytest.raises(EnvironmentError, match="SUPABASE_URL"):
            sc.get_client()

    def test_get_client_raises_on_missing_key(self, monkeypatch):
        """get_client() must raise EnvironmentError when only SUPABASE_SERVICE_ROLE_KEY is missing."""
        monkeypatch.setattr(sc, "_client", None)
        monkeypatch.setenv("SUPABASE_URL", FAKE_URL)
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

        with pytest.raises(EnvironmentError, match="SUPABASE_SERVICE_ROLE_KEY"):
            sc.get_client()

    def test_get_client_returns_singleton(self, monkeypatch):
        """get_client() must return the same instance on repeated calls."""
        mock_client = _make_mock_client()
        monkeypatch.setattr(sc, "_client", mock_client)

        first = sc.get_client()
        second = sc.get_client()

        assert first is second


class TestLogOutputExcludesKey:
    def test_log_output_excludes_key(self, monkeypatch, caplog):
        """
        No log record produced by supabase_client should contain the literal
        SUPABASE_SERVICE_ROLE_KEY value — even when errors are logged.
        """
        monkeypatch.setattr(sc, "_client", None)
        monkeypatch.setenv("SUPABASE_URL", FAKE_URL)
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", FAKE_KEY)

        # Mock create_client so we don't need a real Supabase project
        mock_client = _make_mock_client()
        with patch("research_lab.supabase_client.create_client", return_value=mock_client):
            with caplog.at_level(logging.DEBUG, logger="research_lab.supabase_client"):
                sc.get_client()

                # Also trigger an error path to exercise error log messages
                mock_client.table.return_value.upsert.return_value.execute.side_effect = (
                    RuntimeError("db error")
                )
                sc.upsert_agent_output(
                    session_id=FAKE_SESSION_ID,
                    agent_name="procedure",
                    revision_count=2,
                    output={"data": "value"},
                )

        # The key value must not appear in any log message
        for record in caplog.records:
            assert FAKE_KEY not in record.getMessage(), (
                f"Service role key found in log record: {record.getMessage()!r}"
            )

    def test_log_output_excludes_key_on_init_log(self, monkeypatch, caplog):
        """
        The initialisation log line (which logs the URL) must not include the key.
        """
        monkeypatch.setattr(sc, "_client", None)
        monkeypatch.setenv("SUPABASE_URL", FAKE_URL)
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", FAKE_KEY)

        mock_client = _make_mock_client()
        with patch("research_lab.supabase_client.create_client", return_value=mock_client):
            with caplog.at_level(logging.INFO, logger="research_lab.supabase_client"):
                sc.get_client()

        for record in caplog.records:
            assert FAKE_KEY not in record.getMessage(), (
                f"Service role key found in log record: {record.getMessage()!r}"
            )
