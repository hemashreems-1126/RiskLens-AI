"""
Stage 1: Fraud Detector = Isolation Forest (statistical anomaly) + Rule Engine
(deterministic suspicious-pattern checks), combined into an alert.

This is a real, trained scikit-learn model — not a placeholder. It is
trained on the synthetic dataset's numeric features and produces a
continuous anomaly score, which is combined with rule-engine flags to
decide whether an alert should be raised.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


FEATURE_COLUMNS = [
    "amount",
    "balance_ratio",       # amount / (balance_before + 1)
    "balance_after_ratio",  # balance_after / (balance_before + 1)
]


def _engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["balance_ratio"] = df["amount"] / (df["account_balance_before"] + 1)
    df["balance_after_ratio"] = df["account_balance_after"] / (df["account_balance_before"] + 1)
    return df


class FraudDetector:
    def __init__(self, contamination: float = 0.12, random_state: int = 42):
        self.model = IsolationForest(
            n_estimators=200,
            contamination=contamination,
            random_state=random_state,
        )
        self._fitted = False

    def fit(self, df: pd.DataFrame):
        feats = _engineer_features(df)[FEATURE_COLUMNS]
        self.model.fit(feats)
        self._fitted = True
        return self

    def score(self, df: pd.DataFrame) -> pd.Series:
        """Return a 0-1 anomaly score per row (1 = most anomalous)."""
        if not self._fitted:
            raise RuntimeError("FraudDetector.fit() must be called before score().")
        feats = _engineer_features(df)[FEATURE_COLUMNS]
        raw = self.model.score_samples(feats)  # higher = more normal
        # normalise: invert and min-max scale to 0..1
        inverted = -raw
        norm = (inverted - inverted.min()) / (inverted.max() - inverted.min() + 1e-9)
        return pd.Series(norm, index=df.index)


# ---------------------------------------------------------------------------
# Rule engine: deterministic, explainable, human-auditable checks
# ---------------------------------------------------------------------------

def apply_rule_engine(row: pd.Series, account_history: pd.DataFrame) -> list[str]:
    """Return a list of plain-English rule violations for a single transaction,
    given the account's other transactions (account_history, excluding this row)."""
    reasons = []

    if row["amount"] > 0.8 * (row["account_balance_before"] + 1):
        reasons.append("Transaction amount exceeds 80% of account balance")

    if len(account_history) >= 3:
        recent = account_history.sort_values("timestamp").tail(6)
        window = recent["timestamp"].max() - recent["timestamp"].min()
        if len(recent) >= 3 and window.total_seconds() < 3600:
            reasons.append("Unusually high transaction velocity (3+ transactions within an hour)")

    if len(account_history) > 0:
        usual_locations = set(account_history["location"].value_counts().head(3).index)
        if row["location"] not in usual_locations and len(account_history) >= 5:
            reasons.append("Transaction location differs from account's usual locations")

        usual_devices = set(account_history["device_id"])
        if row["device_id"] not in usual_devices and len(account_history) >= 3:
            reasons.append("Transaction made from a previously unseen device")

        usual_ips = set(account_history["ip_address"])
        if row["ip_address"] not in usual_ips and len(account_history) >= 3:
            reasons.append("Transaction made from a previously unseen IP address")

    if len(account_history) > 0:
        receiver_counts = account_history["receiver"].value_counts()
        if receiver_counts.get(row["receiver"], 0) >= 2:
            reasons.append("Repeated transfers to the same receiver account")

    if row["account_balance_after"] < 0.1 * (row["account_balance_before"] + 1):
        reasons.append("Transaction drains most of the account balance")

    return reasons


def initial_risk_band(anomaly_score: float, n_rule_hits: int) -> str:
    """Cheap first-pass banding used only to prioritise the alert queue.
    The REAL risk score/band used for decisions is computed later by
    app.risk.risk_engine using full agent evidence."""
    combined = 0.6 * anomaly_score + 0.4 * min(n_rule_hits / 4, 1.0)
    if combined >= 0.75:
        return "CRITICAL"
    if combined >= 0.55:
        return "HIGH"
    if combined >= 0.3:
        return "MEDIUM"
    return "LOW"
