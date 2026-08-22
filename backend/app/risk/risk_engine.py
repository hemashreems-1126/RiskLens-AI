"""
Deterministic risk scoring + decision policy.

IMPORTANT DESIGN RULE (see README "AI Design Principle"): the LLM never
invents this number. Everything in this file is plain, auditable Python.
The LLM (Explainability Agent) only narrates what this module already
decided.
"""
from __future__ import annotations
from dataclasses import dataclass

# Weights are intentionally explicit and documented so every point of the
# final score can be traced back to a concrete signal.
WEIGHTS = {
    "anomaly_score": 0.25,       # Isolation Forest output (0-1)
    "behavior_anomaly": 0.20,    # from Behavior Agent findings (0-1)
    "velocity_anomaly": 0.15,    # rapid repeated transactions (0-1)
    "amount_deviation": 0.15,    # how far amount is from account's norm (0-1)
    "balance_drain": 0.10,       # how much of balance this txn removes (0-1)
    "network_risk": 0.10,        # Network Agent risk (0-1)
    "rule_violations": 0.05,     # normalised count of rule-engine hits (0-1)
}

assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-6


def compute_risk_score(signals: dict) -> tuple[float, dict]:
    """signals: dict with keys matching WEIGHTS, each a float 0..1.
    Missing keys default to 0. Returns (score_0_100, contribution_breakdown)."""
    breakdown = {}
    total = 0.0
    for key, weight in WEIGHTS.items():
        value = max(0.0, min(1.0, float(signals.get(key, 0.0))))
        contribution = value * weight * 100
        breakdown[key] = round(contribution, 2)
        total += contribution
    return round(total, 2), breakdown


def risk_level_from_score(score: float) -> str:
    if score >= 81:
        return "CRITICAL"
    if score >= 61:
        return "HIGH"
    if score >= 31:
        return "MEDIUM"
    return "LOW"


def decision_from_risk(risk_level: str, sufficient_evidence: bool, human_override: str | None = None) -> tuple[str, str]:
    """Deterministic policy mapping risk -> ALLOW/REVIEW/BLOCK.

    A human override (ALLOW/BLOCK/ESCALATE from the Reviewer Agent's UI)
    always takes precedence and is recorded as such.
    """
    if human_override:
        mapped = "REVIEW" if human_override == "ESCALATE" else human_override
        return mapped, f"Human reviewer override: {human_override}"

    if not sufficient_evidence:
        return "REVIEW", "Evidence remained insufficient after the maximum investigation loops; routed to human review rather than an automated BLOCK."

    if risk_level == "CRITICAL":
        return "BLOCK", "Risk level CRITICAL — blocked automatically per policy."
    if risk_level == "HIGH":
        return "REVIEW", "Risk level HIGH — requires human review before action."
    if risk_level == "MEDIUM":
        return "REVIEW", "Risk level MEDIUM — borderline case routed to human review."
    return "ALLOW", "Risk level LOW — allowed automatically per policy."
