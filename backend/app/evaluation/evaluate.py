"""
Held-out test set evaluation for the fraud detector.

The synthetic dataset carries a ground-truth is_fraud label (since it was
generated with known injected patterns). We split it into TRAIN and a
HELD-OUT TEST set, fit the Isolation Forest + rule engine on TRAIN only,
then measure precision/recall/F1/FPR/confusion-matrix on TEST only.

These numbers describe the anomaly detector's stand-alone performance on
synthetic data — NOT the full agentic pipeline's real-world accuracy, and
NOT a production guarantee. See README "Evaluation" section.
"""
from __future__ import annotations
import pandas as pd
from sklearn.model_selection import train_test_split

from app.risk.fraud_detector import FraudDetector, apply_rule_engine
from app.config.settings import get_settings

settings = get_settings()


def evaluate_fraud_detector(df: pd.DataFrame, test_size: float = 0.3, random_state: int = 42) -> dict:
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    train_df, test_df = train_test_split(df, test_size=test_size, random_state=random_state, stratify=df["is_fraud"])

    detector = FraudDetector().fit(train_df)
    test_df = test_df.copy()
    test_df["anomaly_score"] = detector.score(test_df)

    predictions = []
    for _, row in test_df.iterrows():
        account_history = train_df[train_df["account_id"] == row["account_id"]]
        rule_hits = apply_rule_engine(row, account_history)
        predicted_fraud = bool(row["anomaly_score"] >= 0.55 or len(rule_hits) >= 2)
        predictions.append(predicted_fraud)

    test_df["predicted_fraud"] = predictions
    actual = test_df["is_fraud"].astype(bool)
    predicted = test_df["predicted_fraud"].astype(bool)

    tp = int(((actual) & (predicted)).sum())
    fp = int((~actual & predicted).sum())
    tn = int((~actual & ~predicted).sum())
    fn = int((actual & ~predicted).sum())

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    accuracy = (tp + tn) / len(test_df) if len(test_df) > 0 else 0.0

    fp_cost = fp * settings.FALSE_POSITIVE_COST
    fn_cost = fn * settings.FALSE_NEGATIVE_COST
    total_cost = fp_cost + fn_cost

    return {
        "test_set_size": int(len(test_df)),
        "train_set_size": int(len(train_df)),
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "false_positive_rate": round(fpr, 4),
        "confusion_matrix": {"true_positives": tp, "false_positives": fp, "true_negatives": tn, "false_negatives": fn},
        "cost_assumptions": {
            "false_positive_cost_per_case": settings.FALSE_POSITIVE_COST,
            "false_negative_cost_per_case": settings.FALSE_NEGATIVE_COST,
            "note": "These are configurable, illustrative assumptions for a synthetic evaluation, not real business figures.",
        },
        "false_positive_cost_total": round(fp_cost, 2),
        "false_negative_cost_total": round(fn_cost, 2),
        "total_estimated_cost": round(total_cost, 2),
        "disclaimer": "These metrics are measured on a held-out synthetic test set and do not represent production accuracy.",
    }
