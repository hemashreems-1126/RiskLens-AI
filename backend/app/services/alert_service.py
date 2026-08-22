"""
Turns raw transactions into Alerts: trains the Isolation Forest on the
current transaction set, scores every transaction, runs the rule engine
per-account, and creates an Alert row for anything that crosses the
anomaly/rule threshold.
"""
from __future__ import annotations
import pandas as pd
from sqlalchemy.orm import Session

from app.models import models
from app.risk.fraud_detector import FraudDetector, apply_rule_engine, initial_risk_band

ANOMALY_ALERT_THRESHOLD = 0.55


def generate_alerts_for_all_transactions(db: Session) -> int:
    txns = db.query(models.Transaction).all()
    if not txns:
        return 0

    rows = [{c.name: getattr(t, c.name) for c in models.Transaction.__table__.columns} for t in txns]
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    detector = FraudDetector().fit(df)
    df["anomaly_score"] = detector.score(df)

    created = 0
    existing_alert_txn_ids = {a.transaction_id for a in db.query(models.Alert.transaction_id).all()}

    for _, row in df.iterrows():
        if row["transaction_id"] in existing_alert_txn_ids:
            continue
        account_history = df[(df["account_id"] == row["account_id"]) & (df["transaction_id"] != row["transaction_id"])]
        rule_hits = apply_rule_engine(row, account_history)

        if row["anomaly_score"] >= ANOMALY_ALERT_THRESHOLD or len(rule_hits) >= 2:
            risk = initial_risk_band(row["anomaly_score"], len(rule_hits))
            alert = models.Alert(
                transaction_id=row["transaction_id"],
                account_id=row["account_id"],
                merchant_id=row["merchant_id"],
                amount=row["amount"],
                transaction_type=row["transaction_type"],
                payment_method=row["payment_method"],
                anomaly_score=round(float(row["anomaly_score"]), 4),
                flag_reason=rule_hits if rule_hits else ["Statistical anomaly (Isolation Forest)"],
                initial_risk=risk,
                status="open",
            )
            db.add(alert)
            created += 1

    db.commit()
    return created
