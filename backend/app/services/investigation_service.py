"""
Orchestration service: takes an Alert, runs it through the compiled
LangGraph investigation graph, and persists every stage's output to
Postgres (transactions, evidence, agent_events, risk_assessments,
decisions, audit_logs).
"""
from __future__ import annotations
import datetime as dt
from sqlalchemy.orm import Session

from app.models import models
from app.graph.investigation_graph import get_investigation_graph
from app.tools.investigation_tools import get_account_history
from app.services.json_utils import sanitize_for_json


def _txn_to_dict(txn: models.Transaction) -> dict:
    return {c.name: getattr(txn, c.name) for c in models.Transaction.__table__.columns}


def run_investigation(db: Session, alert: models.Alert) -> models.Investigation:
    txn = db.query(models.Transaction).filter(models.Transaction.transaction_id == alert.transaction_id).first()
    if txn is None:
        raise ValueError(f"Transaction {alert.transaction_id} not found for alert {alert.alert_id}")

    investigation = models.Investigation(alert_id=alert.alert_id, status="running")
    db.add(investigation)
    db.commit()
    db.refresh(investigation)

    history_df = get_account_history(db, txn.account_id, exclude_transaction_id=txn.transaction_id)
    history_df_json = history_df.assign(
        timestamp=history_df["timestamp"].astype(str)
    ).to_dict(orient="records") if not history_df.empty else []

    initial_state = {
        "case_id": investigation.case_id,
        "investigation_id": investigation.investigation_id,
        "alert": {
            "alert_id": alert.alert_id,
            "anomaly_score": alert.anomaly_score,
            "flag_reason": alert.flag_reason,
            "initial_risk": alert.initial_risk,
        },
        "transaction": {**_txn_to_dict(txn), "timestamp": str(txn.timestamp)},
        "account_history": history_df_json,
        "agent_events": [],
        "audit_events": [],
        "loop_number": 0,
    }

    graph = get_investigation_graph()
    final_state = graph.invoke(initial_state)

    # --- persist everything ---
    investigation.status = final_state.get("investigation_status", "completed")
    investigation.loops_used = final_state.get("loop_number", 0)
    investigation.risk_score = final_state.get("risk_score")
    investigation.risk_level = final_state.get("risk_level")
    investigation.decision = final_state.get("decision")
    investigation.explanation = final_state.get("explanation")
    investigation.llm_mode = final_state.get("llm_mode", "mock")
    investigation.updated_at = dt.datetime.utcnow()

    db.add(models.Evidence(investigation_id=investigation.investigation_id, source="evidence_agent", payload=sanitize_for_json(final_state.get("evidence", {}))))
    db.add(models.Evidence(investigation_id=investigation.investigation_id, source="behavior_agent", payload=sanitize_for_json(final_state.get("behavior_findings", {}))))
    db.add(models.Evidence(investigation_id=investigation.investigation_id, source="network_agent", payload=sanitize_for_json(final_state.get("network_findings", {}))))
    db.add(models.Evidence(investigation_id=investigation.investigation_id, source="compliance_agent", payload=sanitize_for_json(final_state.get("compliance_findings", {}))))

    for e in final_state.get("agent_events", []):
        db.add(models.AgentEvent(
            investigation_id=investigation.investigation_id,
            agent_name=e["agent_name"], status=e["status"],
            finding_summary=e.get("finding_summary"), detail=e.get("detail"),
        ))

    db.add(models.RiskAssessment(
        investigation_id=investigation.investigation_id,
        risk_score=final_state.get("risk_score", 0),
        risk_level=final_state.get("risk_level", "LOW"),
        signal_breakdown=sanitize_for_json(final_state.get("risk_factors", {})),
        loop_number=final_state.get("loop_number", 0),
        sufficient_evidence=final_state.get("sufficient_evidence", True),
    ))

    db.add(models.DecisionRecord(
        investigation_id=investigation.investigation_id,
        decision=final_state.get("decision", "REVIEW"),
        rationale=final_state.get("decision_rationale", ""),
    ))

    for a in final_state.get("audit_events", []):
        db.add(models.AuditLog(
            investigation_id=investigation.investigation_id,
            stage=a["stage"], actor=a["actor"], action=a["action"], detail=a.get("detail"),
        ))

    alert.status = "investigating" if investigation.status == "awaiting_review" else "closed"
    db.add(alert)
    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    return investigation


def apply_human_review(db: Session, investigation: models.Investigation, reviewer_decision: str, notes: str | None) -> models.Investigation:
    from app.risk.risk_engine import decision_from_risk

    db.add(models.HumanReview(investigation_id=investigation.investigation_id, reviewer_decision=reviewer_decision, notes=notes))

    final_decision, rationale = decision_from_risk(investigation.risk_level or "LOW", True, human_override=reviewer_decision)
    investigation.decision = final_decision
    investigation.status = "completed"
    investigation.updated_at = dt.datetime.utcnow()

    db.add(models.DecisionRecord(investigation_id=investigation.investigation_id, decision=final_decision, rationale=rationale))
    db.add(models.AuditLog(investigation_id=investigation.investigation_id, stage="human_review", actor="human:analyst", action="review_submitted", detail={"reviewer_decision": reviewer_decision, "notes": notes}))
    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    return investigation


def apply_feedback(db: Session, investigation: models.Investigation, was_correct: bool, comment: str | None) -> models.Feedback:
    fb = models.Feedback(investigation_id=investigation.investigation_id, was_correct=was_correct, comment=comment)
    db.add(fb)
    db.add(models.AuditLog(investigation_id=investigation.investigation_id, stage="feedback", actor="human:analyst", action="feedback_submitted", detail={"was_correct": was_correct, "comment": comment}))
    db.commit()
    db.refresh(fb)
    return fb
