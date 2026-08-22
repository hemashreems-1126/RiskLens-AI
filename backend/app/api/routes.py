"""FastAPI routes — the full public surface of RiskLens AI."""
from __future__ import annotations
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models import models
from app.schemas import schemas
from app.services import investigation_service, alert_service
from app.services.data_generator import generate_dataset_for_db
from app.evaluation.evaluate import evaluate_fraud_detector
from app.config.settings import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
def health():
    return {"status": "ok", "llm_mode": "mock" if settings.LLM_MOCK_MODE else "live", "groq_model": settings.GROQ_MODEL}


@router.get("/api/dashboard/summary", response_model=schemas.DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    total_txns = db.query(models.Transaction).count()
    alerts = db.query(models.Alert).all()
    suspicious = len(alerts)
    investigations = db.query(models.Investigation).all()
    high_risk = sum(1 for i in investigations if i.risk_level in ("HIGH", "CRITICAL"))
    blocked = sum(1 for i in investigations if i.decision == "BLOCK")
    pending_review = sum(1 for i in investigations if i.status == "awaiting_review")

    eval_metrics = _cached_eval(db)

    return schemas.DashboardSummary(
        total_transactions=total_txns,
        suspicious_transactions=suspicious,
        high_risk=high_risk,
        blocked=blocked,
        pending_review=pending_review,
        fraud_precision=eval_metrics.get("precision", 0.0),
        fraud_recall=eval_metrics.get("recall", 0.0),
        f1_score=eval_metrics.get("f1_score", 0.0),
        false_positive_rate=eval_metrics.get("false_positive_rate", 0.0),
        false_positive_cost=eval_metrics.get("false_positive_cost_total", 0.0),
    )


_eval_cache: dict = {}


def _cached_eval(db: Session) -> dict:
    if _eval_cache:
        return _eval_cache
    txns = db.query(models.Transaction).all()
    if not txns:
        return {}
    rows = [{c.name: getattr(t, c.name) for c in models.Transaction.__table__.columns} for t in txns]
    df = pd.DataFrame(rows)
    metrics = evaluate_fraud_detector(df)
    _eval_cache.update(metrics)
    return metrics


@router.get("/api/evaluation")
def get_evaluation(db: Session = Depends(get_db)):
    _eval_cache.clear()
    metrics = _cached_eval(db)
    if not metrics:
        raise HTTPException(404, "No transaction data available yet. POST /api/demo/reset first.")
    return metrics


@router.get("/api/transactions", response_model=list[schemas.TransactionOut])
def list_transactions(limit: int = 200, db: Session = Depends(get_db)):
    return db.query(models.Transaction).order_by(models.Transaction.timestamp.desc()).limit(limit).all()


@router.get("/api/transactions/{transaction_id}", response_model=schemas.TransactionOut)
def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    txn = db.query(models.Transaction).filter(models.Transaction.transaction_id == transaction_id).first()
    if not txn:
        raise HTTPException(404, "Transaction not found")
    return txn


@router.get("/api/alerts", response_model=list[schemas.AlertOut])
def list_alerts(db: Session = Depends(get_db)):
    return db.query(models.Alert).order_by(models.Alert.timestamp.desc()).all()


@router.get("/api/alerts/{alert_id}", response_model=schemas.AlertOut)
def get_alert(alert_id: str, db: Session = Depends(get_db)):
    alert = db.query(models.Alert).filter(models.Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(404, "Alert not found")
    return alert


@router.post("/api/investigations", response_model=schemas.InvestigationOut)
def start_investigation(payload: schemas.InvestigationCreate, db: Session = Depends(get_db)):
    alert = db.query(models.Alert).filter(models.Alert.alert_id == payload.alert_id).first()
    if not alert:
        raise HTTPException(404, "Alert not found")
    try:
        investigation = investigation_service.run_investigation(db, alert)
    except Exception as exc:  # noqa: BLE001 — graceful failure, not a crash
        raise HTTPException(500, f"Investigation failed but was not silently faked: {exc}")
    return investigation


@router.get("/api/investigations/{investigation_id}", response_model=schemas.InvestigationOut)
def get_investigation(investigation_id: str, db: Session = Depends(get_db)):
    inv = db.query(models.Investigation).filter(models.Investigation.investigation_id == investigation_id).first()
    if not inv:
        raise HTTPException(404, "Investigation not found")
    return inv


@router.post("/api/investigations/{investigation_id}/review", response_model=schemas.InvestigationOut)
def review_investigation(investigation_id: str, payload: schemas.ReviewIn, db: Session = Depends(get_db)):
    inv = db.query(models.Investigation).filter(models.Investigation.investigation_id == investigation_id).first()
    if not inv:
        raise HTTPException(404, "Investigation not found")
    if payload.reviewer_decision not in ("ALLOW", "BLOCK", "ESCALATE"):
        raise HTTPException(400, "reviewer_decision must be ALLOW, BLOCK or ESCALATE")
    return investigation_service.apply_human_review(db, inv, payload.reviewer_decision, payload.notes)


@router.post("/api/investigations/{investigation_id}/feedback")
def submit_feedback(investigation_id: str, payload: schemas.FeedbackIn, db: Session = Depends(get_db)):
    inv = db.query(models.Investigation).filter(models.Investigation.investigation_id == investigation_id).first()
    if not inv:
        raise HTTPException(404, "Investigation not found")
    fb = investigation_service.apply_feedback(db, inv, payload.was_correct, payload.comment)
    return {"feedback_id": fb.feedback_id, "stored": True}


@router.get("/api/investigations/{investigation_id}/audit")
def get_audit_trail(investigation_id: str, db: Session = Depends(get_db)):
    inv = db.query(models.Investigation).filter(models.Investigation.investigation_id == investigation_id).first()
    if not inv:
        raise HTTPException(404, "Investigation not found")
    logs = db.query(models.AuditLog).filter(models.AuditLog.investigation_id == investigation_id).order_by(models.AuditLog.timestamp).all()
    return [{"stage": l.stage, "actor": l.actor, "action": l.action, "detail": l.detail, "timestamp": l.timestamp} for l in logs]


@router.post("/api/demo/reset")
def demo_reset(db: Session = Depends(get_db)):
    """Wipes and reseeds demo data: fresh synthetic transactions + freshly
    generated alerts, so judges always see a populated dashboard."""
    for model in [models.AuditLog, models.Feedback, models.HumanReview, models.DecisionRecord,
                  models.RiskAssessment, models.AgentEvent, models.Evidence, models.Investigation,
                  models.Alert, models.Transaction]:
        db.query(model).delete()
    db.commit()
    _eval_cache.clear()

    rows = generate_dataset_for_db()
    for row in rows:
        db.add(models.Transaction(**row))
    db.commit()

    n_alerts = alert_service.generate_alerts_for_all_transactions(db)
    return {"transactions_created": len(rows), "alerts_created": n_alerts}
