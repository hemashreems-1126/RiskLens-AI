"""
Shared structured state passed between every node of the LangGraph
investigation graph. This is the "Shared Case Memory" described in the
architecture — a typed dict, not a blob of unstructured text.
"""
from __future__ import annotations
from typing import TypedDict, Optional, Any


class CaseState(TypedDict, total=False):
    case_id: str
    investigation_id: str
    alert: dict
    transaction: dict
    account_history: list  # list[dict] — serialisable snapshot of prior txns

    evidence: dict
    behavior_findings: dict
    network_findings: dict
    compliance_findings: dict

    risk_factors: dict
    risk_score: float
    risk_level: str
    loop_number: int
    sufficient_evidence: bool

    agent_events: list  # list[dict]: {agent_name, status, finding_summary, detail}

    investigation_status: str
    decision: Optional[str]
    decision_rationale: Optional[str]
    human_review: Optional[dict]
    explanation: Optional[str]
    llm_mode: str

    feedback: Optional[dict]
    audit_events: list  # list[dict]
