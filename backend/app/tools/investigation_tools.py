"""
Deterministic tools used by the investigation agents. These are plain
Python functions over the database/dataframe — they return FACTS only.
Agents reason over what these functions return; agents never invent
facts themselves.
"""
from __future__ import annotations
import pandas as pd
from sqlalchemy.orm import Session

from app.models.models import Transaction


def get_account_history(db: Session, account_id: str, exclude_transaction_id: str | None = None) -> pd.DataFrame:
    q = db.query(Transaction).filter(Transaction.account_id == account_id)
    rows = [
        {c.name: getattr(t, c.name) for c in Transaction.__table__.columns}
        for t in q.all()
        if t.transaction_id != exclude_transaction_id
    ]
    return pd.DataFrame(rows)


def amount_comparison(txn: dict, history: pd.DataFrame) -> dict:
    if history.empty:
        return {"has_history": False, "amount_deviation": 0.5, "note": "No prior history for this account — cannot establish a baseline."}
    mean = history["amount"].mean()
    std = history["amount"].std() or 1.0
    z = (txn["amount"] - mean) / std
    deviation = min(1.0, max(0.0, abs(z) / 4))  # squashed to 0..1
    return {
        "has_history": True,
        "account_avg_amount": round(float(mean), 2),
        "account_std_amount": round(float(std), 2),
        "z_score": round(float(z), 2),
        "amount_deviation": round(deviation, 3),
    }


def transaction_frequency(history: pd.DataFrame) -> dict:
    if history.empty or len(history) < 2:
        return {"velocity_anomaly": 0.0, "note": "Not enough history to assess velocity."}
    hist = history.copy()
    hist["timestamp"] = pd.to_datetime(hist["timestamp"])
    hist = hist.sort_values("timestamp")
    recent = hist.tail(6)
    span_minutes = max(1.0, (recent["timestamp"].max() - recent["timestamp"].min()).total_seconds() / 60)
    txns_per_hour = len(recent) / (span_minutes / 60)
    velocity_anomaly = min(1.0, txns_per_hour / 6)  # 6+ txns/hour treated as fully anomalous
    return {
        "recent_transaction_count": int(len(recent)),
        "span_minutes": round(span_minutes, 1),
        "txns_per_hour": round(txns_per_hour, 2),
        "velocity_anomaly": round(velocity_anomaly, 3),
    }


def balance_impact(txn: dict) -> dict:
    before = txn["account_balance_before"]
    after = txn["account_balance_after"]
    drained_fraction = 1 - (after / (before + 1)) if before > 0 else 1.0
    drained_fraction = min(1.0, max(0.0, drained_fraction))
    return {"balance_drain": round(drained_fraction, 3)}


def transaction_type_history(txn: dict, history: pd.DataFrame) -> dict:
    if history.empty:
        return {"type_is_unusual": False, "note": "No history available."}
    common_types = set(history["transaction_type"].value_counts().head(2).index)
    return {"type_is_unusual": txn["transaction_type"] not in common_types, "common_types": list(common_types)}


def network_relationships(txn: dict, history: pd.DataFrame) -> dict:
    findings = {"shared_device_flag": False, "shared_ip_flag": False, "repeated_receiver": False, "network_risk": 0.0}
    score = 0.0
    if not history.empty:
        if txn["device_id"] not in set(history["device_id"]):
            findings["shared_device_flag"] = True  # i.e. NEW/unrecognised device
            score += 0.35
        if txn["ip_address"] not in set(history["ip_address"]):
            findings["shared_ip_flag"] = True
            score += 0.25
        receiver_counts = history["receiver"].value_counts()
        if receiver_counts.get(txn["receiver"], 0) >= 2:
            findings["repeated_receiver"] = True
            score += 0.4
    findings["network_risk"] = round(min(1.0, score), 3)
    return findings


def compliance_checks(txn: dict, history: pd.DataFrame) -> dict:
    """Deterministic, rule-based, clearly-synthetic compliance checks.
    These are NOT real regulatory rules — they are illustrative thresholds
    for the buildathon demo and are labelled as such."""
    violations = []
    if txn["amount"] > 200000:
        violations.append("SYNTHETIC RULE: single transaction exceeds ₹2,00,000 reporting threshold")
    if not history.empty:
        failed = history[history.get("transaction_status", "completed") == "failed"] if "transaction_status" in history.columns else history.iloc[0:0]
        if len(failed) >= 2:
            violations.append("SYNTHETIC RULE: 2+ recent failed transactions on this account")
    return {"rule_violations": violations, "rule_violation_count": len(violations)}
