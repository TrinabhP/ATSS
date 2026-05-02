"""
critic_agent.py — Standalone critic agent for LabOS Research Analysis Engine.

Responsibilities:
  1. Review literature findings produced by the literature agent.
  2. Generate substantive, evidence-grounded critiques.
  3. Conduct an iterative debate with the results agent:
       Critic critique → Results agent response → Critic rebuttal → … (up to MAX_ROUNDS)
  4. Emit a final debate summary once convergence is reached or rounds are exhausted.

Usage (standalone):
    from critic_agent import CriticAgent
    critic = CriticAgent()
    critique = critic.critique_findings(literature_findings, initial_synthesis)
    summary  = critic.run_debate(results_agent_fn, literature_findings, initial_synthesis)

Usage (as part of the pipeline):
    The results agent calls critic.next_round(results_response) each turn and receives
    either a new rebuttal string or None when the critic concedes / rounds are exhausted.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable, List, Optional

import anthropic

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL = "claude-sonnet-4-20250514"
MAX_ROUNDS = 3

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_INITIAL_CRITIQUE_SYSTEM = """You are a rigorous scientific critic embedded in a multi-agent research pipeline.

You will receive:
  - A list of literature findings (papers, extracted results, or a synthesis).
  - An initial analysis or synthesis produced by another agent.

Your job is to produce a sharp, specific critique of that analysis. Focus on:
  1. Sample-size issues — underpowered studies, small n, lack of statistical power.
  2. Confounding variables — factors not controlled for that could explain the results.
  3. Overgeneralisation — claims that go beyond what the data actually shows.
  4. Statistical concerns — p-hacking, multiple comparisons, effect sizes, CI widths.
  5. Publication bias — missing contradictory evidence, selective reporting.
  6. Methodological heterogeneity — comparing studies with incompatible designs.

Rules:
  - Cite specific paper titles or findings when making a criticism.
  - Write exactly 3 concise paragraphs (one per major concern — pick the strongest three).
  - Do NOT hedge excessively; take clear positions.
  - Do NOT simply agree with the analysis; find genuine weaknesses.
  - Output plain text only — no JSON, no markdown headers."""

_REBUTTAL_SYSTEM = """You are a rigorous scientific critic in an ongoing debate with a results agent.

You have already issued a critique. The results agent has responded, either confirming, refuting, or partially validating each concern.

Your job now is to issue a rebuttal. Rules:
  1. For each concern the results agent CONFIRMED — acknowledge it briefly and escalate: demand the analysis explicitly caveat or retract the affected claim.
  2. For each concern the results agent REFUTED — challenge the rebuttal if the numbers are insufficient, OR concede the point explicitly if the evidence is compelling.
  3. For each concern the results agent PARTIALLY VALIDATED — press for a stronger concession or a clearer caveat in the final synthesis.
  4. If the results agent has genuinely addressed all your major concerns, say so explicitly and signal that the debate can close.

Write 2–3 paragraphs. Be direct and cite specifics.
Output plain text only — no JSON, no markdown headers."""

_SUMMARY_SYSTEM = """You are a scientific critic producing a post-debate summary.

You will receive the full debate transcript (each round's critique and the results agent's response).

Produce a structured plain-text summary with these four sections (use these exact headers):

RESOLVED CONCERNS
List each concern that was fully addressed, with one sentence explaining why it was resolved.

OUTSTANDING CONCERNS
List each concern that was NOT adequately addressed, with one sentence explaining what evidence is still missing.

NET IMPACT ON CONFIDENCE
One sentence: did the debate raise, lower, or leave unchanged the confidence in the original analysis, and why?

RECOMMENDED CAVEATS
Bullet list of 1–3 caveats that MUST appear in the final synthesis based on this debate.

Output plain text only — no JSON."""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DebateTurn:
    round_number: int
    critic_critique: str
    results_response: str = ""   # Filled in by the results agent


@dataclass
class CriticAgent:
    """
    Manages the full critic lifecycle: initial critique, iterative rebuttal,
    and final debate summary.

    Typical flow
    ------------
    1. critic.critique_findings(...)         → initial critique string
    2. results_agent reads critique and responds
    3. critic.next_round(results_response)   → rebuttal string (or None if done)
    4. repeat 2-3 until next_round returns None
    5. critic.debate_summary()               → plain-text summary
    """

    max_rounds: int = MAX_ROUNDS
    _client: Optional[anthropic.Anthropic] = field(default=None, repr=False, init=False)
    _history: List[DebateTurn] = field(default_factory=list, repr=False, init=False)
    _literature_context: str = field(default="", repr=False, init=False)
    _initial_synthesis: str = field(default="", repr=False, init=False)
    _debate_closed: bool = field(default=False, repr=False, init=False)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic(
                api_key=os.environ.get("ANTHROPIC_API_KEY")
            )
        return self._client

    def _call(self, system: str, user_content: str, max_tokens: int = 2048) -> str:
        client = self._get_client()
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user_content}],
            )
            for block in response.content:
                if block.type == "text":
                    return block.text
            return ""
        except anthropic.APIError as e:
            # One retry
            try:
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user_content}],
                )
                for block in response.content:
                    if block.type == "text":
                        return block.text
                return ""
            except Exception as retry_err:
                return f"[CriticAgent API error after retry: {retry_err}]"
        except Exception as e:
            return f"[CriticAgent error: {e}]"

    def _current_round(self) -> int:
        return len(self._history)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def critique_findings(
        self,
        literature_findings: str,
        initial_synthesis: str,
    ) -> str:
        """
        Step 1 — Generate the initial critique from raw literature findings
        and the initial synthesis produced by another agent.

        Parameters
        ----------
        literature_findings : str
            JSON or plain-text dump of papers / extracted results from the
            literature agent.
        initial_synthesis : str
            The synthesis text that this critic will challenge.

        Returns
        -------
        str
            Plain-text critique (3 paragraphs).
        """
        self._literature_context = literature_findings
        self._initial_synthesis = initial_synthesis
        self._history.clear()
        self._debate_closed = False

        user_content = (
            f"Literature findings:\n{literature_findings}\n\n"
            f"Initial synthesis to critique:\n{initial_synthesis}"
        )
        critique = self._call(_INITIAL_CRITIQUE_SYSTEM, user_content)

        # Record the first turn (results_response filled in later)
        self._history.append(DebateTurn(round_number=1, critic_critique=critique))
        return critique

    def next_round(self, results_response: str) -> Optional[str]:
        """
        Step 2…N — Receive the results agent's response and produce a rebuttal.

        Call this after the results agent has replied to the most recent critique.
        Returns None when the debate should close (max rounds reached or critic
        explicitly concedes).

        Parameters
        ----------
        results_response : str
            Plain-text response from the results agent to the last critique.

        Returns
        -------
        str | None
            Rebuttal text, or None if the debate is over.
        """
        if self._debate_closed:
            return None

        if not self._history:
            raise RuntimeError(
                "Call critique_findings() before next_round()."
            )

        # Record the results agent's reply on the current open turn
        self._history[-1].results_response = results_response

        # Check round limit
        if self._current_round() >= self.max_rounds:
            self._debate_closed = True
            return None

        # Build transcript context for the rebuttal prompt
        transcript = self._build_transcript()
        user_content = (
            f"Original literature findings (for reference):\n{self._literature_context}\n\n"
            f"Debate transcript so far:\n{transcript}\n\n"
            f"Results agent's latest response:\n{results_response}"
        )
        rebuttal = self._call(_REBUTTAL_SYSTEM, user_content)

        # Detect explicit concession
        concession_signals = [
            "debate can close",
            "no further concerns",
            "all concerns addressed",
            "satisfied with",
            "adequately addressed",
        ]
        if any(sig in rebuttal.lower() for sig in concession_signals):
            self._debate_closed = True
            self._history.append(
                DebateTurn(
                    round_number=self._current_round() + 1,
                    critic_critique=rebuttal,
                )
            )
            return rebuttal  # Final statement before closing

        self._history.append(
            DebateTurn(
                round_number=self._current_round() + 1,
                critic_critique=rebuttal,
            )
        )
        return rebuttal

    def record_final_response(self, results_response: str) -> None:
        """
        Record the results agent's final response on the last open turn
        (call this after the last next_round() returns None).
        """
        if self._history and not self._history[-1].results_response:
            self._history[-1].results_response = results_response

    def debate_summary(self) -> str:
        """
        Produce a structured post-debate summary after all rounds are complete.

        Returns
        -------
        str
            Plain-text summary with four labelled sections.
        """
        transcript = self._build_transcript()
        user_content = (
            f"Original synthesis:\n{self._initial_synthesis}\n\n"
            f"Full debate transcript:\n{transcript}"
        )
        return self._call(_SUMMARY_SYSTEM, user_content, max_tokens=2048)

    def is_closed(self) -> bool:
        """True once the debate has concluded (max rounds or concession)."""
        return self._debate_closed

    def get_history(self) -> List[DebateTurn]:
        """Return a copy of the debate history."""
        return list(self._history)

    # ------------------------------------------------------------------
    # Convenience: run the full debate automatically
    # ------------------------------------------------------------------

    def run_debate(
        self,
        results_agent_fn: Callable[[str], str],
        literature_findings: str,
        initial_synthesis: str,
    ) -> str:
        """
        Run the full debate loop automatically.

        Parameters
        ----------
        results_agent_fn : Callable[[str], str]
            A function that accepts the critic's critique/rebuttal and returns
            the results agent's plain-text response.
        literature_findings : str
            Raw literature findings string.
        initial_synthesis : str
            Initial synthesis to challenge.

        Returns
        -------
        str
            Plain-text debate summary.
        """
        critique = self.critique_findings(literature_findings, initial_synthesis)

        while not self.is_closed():
            response = results_agent_fn(critique)
            critique = self.next_round(response)
            if critique is None:
                # Record the final response if there was one
                self.record_final_response(response)
                break

        return self.debate_summary()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_transcript(self) -> str:
        parts: List[str] = []
        for turn in self._history:
            parts.append(f"--- Round {turn.round_number} ---")
            parts.append(f"[CRITIC]\n{turn.critic_critique}")
            if turn.results_response:
                parts.append(f"[RESULTS AGENT]\n{turn.results_response}")
        return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Standalone smoke-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    DEMO_FINDINGS = """
    Paper 1: "Menin inhibitor efficacy in NPM1-mutant AML" (n=12, single-arm phase I)
      - 6/12 patients showed HOX gene downregulation (p=0.04)
      - No control arm; no adjustment for co-mutations

    Paper 2: "HOX gene expression as a biomarker in AML" (n=340, retrospective)
      - High HOXA9 correlated with poor OS (HR=1.8, 95% CI 1.2–2.7)
      - Confounding: cytogenetic risk not fully stratified
    """

    DEMO_SYNTHESIS = (
        "Collective evidence strongly suggests HOX gene expression predicts "
        "menin inhibitor response in NPM1-mutant AML. Both papers support this "
        "conclusion with statistically significant results."
    )

    def mock_results_agent(critique: str) -> str:
        return (
            "CONFIRMED: The small sample size of Paper 1 (n=12) is a genuine limitation. "
            "REFUTED: Paper 2 did adjust for cytogenetic risk in the multivariate model (HR=1.8 after adjustment). "
            "PARTIALLY VALIDATED: We agree the p=0.04 threshold warrants caution given multiple comparisons."
        )

    print("=== CriticAgent smoke-test ===\n")
    critic = CriticAgent(max_rounds=2)

    print("[Step 1] Initial critique:")
    critique = critic.critique_findings(DEMO_FINDINGS, DEMO_SYNTHESIS)
    print(critique)

    print("\n[Step 2] Simulated results agent response:")
    response = mock_results_agent(critique)
    print(response)

    print("\n[Step 3] Critic rebuttal:")
    rebuttal = critic.next_round(response)
    print(rebuttal if rebuttal else "(debate closed)")

    print("\n[Step 4] Debate summary:")
    summary = critic.debate_summary()
    print(summary)

    print(f"\nRounds completed: {critic._current_round()}")
    print("Smoke-test complete.")
