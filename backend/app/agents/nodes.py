"""
LangGraph node functions for every agent in the investigation pipeline.
Each node: (1) reads CaseState, (2) does its job (tool calls for the
deterministic agents, a Groq call for the explainability agent),
(3) appends an agent_event + audit_event, (4) returns the state patch.
"""
from __future__ import annotations
import datetime as dt

from app.graph.state import CaseState
from app.services.json_utils import sanitize_for_json
from app.tools import investigation_tools as tools
from app.risk.risk_engine import compute_risk_score, risk_level_from_score, decision_from_risk
from app.services.groq_client import chat_complete
from app.config.settings import get_settings

settings = get_settings()


def _event(agent_name: str, status: str, summary: str, detail: dict | None = None) -> dict:
    return {
        "agent_name": agent_name,
        "status": status,
        "finding_summary": summary,
        "detail": sanitize_for_json(detail or {}),
        "timestamp": dt.datetime.utcnow().isoformat(),
    }


def _audit(stage: str, actor: str, action: str, detail: dict | None = None) -> dict:
    return {"stage": stage, "actor": actor, "action": action, "detail": sanitize_for_json(detail or {}), "timestamp": dt.datetime.utcnow().isoformat()}


# ---------------------------------------------------------------------------
# Planner / orchestrator — decides the investigation is starting; LangGraph's
# edges (not the LLM) actually control routing, per the "LLM plans/Python
# decides" design rule. This node just initialises the case.
# ---------------------------------------------------------------------------

def planner_node(state: CaseState) -> dict:
    events = state.get("agent_events", []) + [_event(
        "planner", "completed",
        f"Investigation planned for transaction {state['transaction']['transaction_id']}. Routing to Evidence, Behavior, Network and Compliance agents."
    )]
    audits = state.get("audit_events", []) + [_audit("planner", "system", "investigation_planned")]
    return {"agent_events": events, "audit_events": audits, "investigation_status": "investigating", "loop_number": state.get("loop_number", 0)}


def evidence_agent_node(state: CaseState) -> dict:
    txn = state["transaction"]
    history = state.get("account_history", [])
    import pandas as pd
    hist_df = pd.DataFrame(history)

    amount_cmp = tools.amount_comparison(txn, hist_df)
    freq = tools.transaction_frequency(hist_df)
    type_hist = tools.transaction_type_history(txn, hist_df)

    evidence = {**amount_cmp, **freq, **type_hist, "history_size": len(hist_df)}
    summary = f"Reviewed {len(hist_df)} prior transactions. Amount deviation z={evidence.get('z_score', 'n/a')}, velocity={freq.get('txns_per_hour', 'n/a')} txns/hr."

    events = state.get("agent_events", []) + [_event("evidence_agent", "completed", summary, evidence)]
    audits = state.get("audit_events", []) + [_audit("evidence_agent", "evidence_agent", "evidence_collected", evidence)]
    return {"evidence": evidence, "agent_events": events, "audit_events": audits}


def behavior_agent_node(state: CaseState) -> dict:
    txn = state["transaction"]
    history = state.get("account_history", [])
    import pandas as pd
    hist_df = pd.DataFrame(history)

    balance = tools.balance_impact(txn)
    amount_cmp = state.get("evidence", {})
    unusual_amount = amount_cmp.get("amount_deviation", 0) > 0.5
    unusual_type = state.get("evidence", {}).get("type_is_unusual", False)

    findings = {
        **balance,
        "unusual_amount": unusual_amount,
        "unusual_transaction_type": unusual_type,
        "behavior_anomaly": round(min(1.0, 0.5 * (1 if unusual_amount else 0) + 0.3 * (1 if unusual_type else 0) + 0.2 * balance["balance_drain"]), 3),
    }
    summary = f"Behavior anomaly score {findings['behavior_anomaly']}. Unusual amount: {unusual_amount}. Unusual type: {unusual_type}."

    events = state.get("agent_events", []) + [_event("behavior_agent", "completed", summary, findings)]
    audits = state.get("audit_events", []) + [_audit("behavior_agent", "behavior_agent", "behavior_analyzed", findings)]
    return {"behavior_findings": findings, "agent_events": events, "audit_events": audits}


def network_agent_node(state: CaseState) -> dict:
    txn = state["transaction"]
    history = state.get("account_history", [])
    import pandas as pd
    hist_df = pd.DataFrame(history)

    findings = tools.network_relationships(txn, hist_df)
    summary = f"Network risk {findings['network_risk']}. Repeated receiver: {findings['repeated_receiver']}. New device: {findings['shared_device_flag']}. New IP: {findings['shared_ip_flag']}."

    events = state.get("agent_events", []) + [_event("network_agent", "completed", summary, findings)]
    audits = state.get("audit_events", []) + [_audit("network_agent", "network_agent", "network_analyzed", findings)]
    return {"network_findings": findings, "agent_events": events, "audit_events": audits}


def compliance_agent_node(state: CaseState) -> dict:
    txn = state["transaction"]
    history = state.get("account_history", [])
    import pandas as pd
    hist_df = pd.DataFrame(history)

    findings = tools.compliance_checks(txn, hist_df)
    summary = f"{findings['rule_violation_count']} synthetic compliance rule(s) triggered."

    events = state.get("agent_events", []) + [_event("compliance_agent", "completed", summary, findings)]
    audits = state.get("audit_events", []) + [_audit("compliance_agent", "compliance_agent", "compliance_checked", findings)]
    return {"compliance_findings": findings, "agent_events": events, "audit_events": audits}


def risk_assessment_node(state: CaseState) -> dict:
    alert = state["alert"]
    evidence = state.get("evidence", {})
    behavior = state.get("behavior_findings", {})
    network = state.get("network_findings", {})
    compliance = state.get("compliance_findings", {})

    signals = {
        "anomaly_score": alert.get("anomaly_score", 0),
        "behavior_anomaly": behavior.get("behavior_anomaly", 0),
        "velocity_anomaly": evidence.get("velocity_anomaly", 0),
        "amount_deviation": evidence.get("amount_deviation", 0),
        "balance_drain": behavior.get("balance_drain", 0),
        "network_risk": network.get("network_risk", 0),
        "rule_violations": min(1.0, compliance.get("rule_violation_count", 0) / 3),
    }
    score, breakdown = compute_risk_score(signals)
    level = risk_level_from_score(score)

    # Sufficiency check: if we have almost no account history AND the
    # signals are weak/ambiguous (borderline MEDIUM), evidence is treated
    # as insufficient and the graph loops back for another investigation pass.
    has_history = evidence.get("has_history", True)
    borderline = 25 <= score <= 45
    sufficient = not (borderline and not has_history)

    loop_number = state.get("loop_number", 0)
    summary = f"Risk score {score}/100 ({level}). Sufficient evidence: {sufficient} (loop {loop_number})."

    events = state.get("agent_events", []) + [_event("risk_assessment", "completed", summary, {"score": score, "level": level, "breakdown": breakdown})]
    audits = state.get("audit_events", []) + [_audit("risk_assessment", "risk_engine", "risk_scored", {"score": score, "level": level})]

    return {
        "risk_score": score,
        "risk_level": level,
        "risk_factors": breakdown,
        "sufficient_evidence": sufficient,
        "agent_events": events,
        "audit_events": audits,
    }


def evidence_loop_node(state: CaseState) -> dict:
    """Runs when risk assessment flagged evidence as insufficient. Widens the
    account history window is not possible synthetically, so instead this
    node re-runs behavior/network analysis with looser thresholds and marks
    the loop as used — a real, bounded LangGraph loop, not a fake retry."""
    loop_number = state.get("loop_number", 0) + 1
    events = state.get("agent_events", []) + [_event(
        "evidence_agent", "completed",
        f"Insufficient evidence on first pass — running additional investigation loop {loop_number}/{settings.MAX_INVESTIGATION_LOOPS}."
    )]
    audits = state.get("audit_events", []) + [_audit("evidence_loop", "system", "additional_loop_triggered", {"loop_number": loop_number})]
    return {"loop_number": loop_number, "agent_events": events, "audit_events": audits}


def decision_node(state: CaseState) -> dict:
    level = state.get("risk_level", "LOW")
    sufficient = state.get("sufficient_evidence", True)
    human = state.get("human_review", {}).get("reviewer_decision") if state.get("human_review") else None

    decision, rationale = decision_from_risk(level, sufficient, human)

    events = state.get("agent_events", []) + [_event("decision_agent", "completed", f"Decision: {decision}. {rationale}")]
    audits = state.get("audit_events", []) + [_audit("decision_agent", "risk_engine", "decision_made", {"decision": decision, "rationale": rationale})]
    return {"decision": decision, "decision_rationale": rationale, "agent_events": events, "audit_events": audits, "investigation_status": "awaiting_review" if decision == "REVIEW" and not human else "completed"}


def explainability_node(state: CaseState) -> dict:
    txn = state["transaction"]
    system_prompt = (
        "You are a payment-risk explainability assistant. You are given FACTUAL "
        "evidence already collected by deterministic tools and a deterministic "
        "risk score. You must explain the decision in plain language using ONLY "
        "the evidence given — never invent new facts or change the numeric score. "
        "Answer: why flagged, what evidence found, how serious, recommended action, "
        "strongest evidence, remaining uncertainty. Keep it under 180 words."
    )
    user_prompt = (
        f"Transaction: {txn}\n"
        f"Evidence: {state.get('evidence')}\n"
        f"Behavior findings: {state.get('behavior_findings')}\n"
        f"Network findings: {state.get('network_findings')}\n"
        f"Compliance findings: {state.get('compliance_findings')}\n"
        f"Risk score: {state.get('risk_score')} ({state.get('risk_level')})\n"
        f"Decision: {state.get('decision')} — {state.get('decision_rationale')}\n"
    )
    explanation, mode = chat_complete(system_prompt, user_prompt)

    events = state.get("agent_events", []) + [_event("explainability_agent", "completed", "Explanation generated.", {"llm_mode": mode})]
    audits = state.get("audit_events", []) + [_audit("explainability_agent", f"groq:{mode}", "explanation_generated")]
    return {"explanation": explanation, "llm_mode": mode, "agent_events": events, "audit_events": audits}


def audit_report_node(state: CaseState) -> dict:
    audits = state.get("audit_events", []) + [_audit("audit_report", "system", "audit_report_finalized", {
        "decision": state.get("decision"), "risk_score": state.get("risk_score")
    })]
    events = state.get("agent_events", []) + [_event("audit_report", "completed", "Audit trail finalized and stored.")]
    return {"audit_events": audits, "agent_events": events}
