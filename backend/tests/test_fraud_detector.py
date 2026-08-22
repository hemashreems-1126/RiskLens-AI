import pandas as pd
from app.services.data_generator import generate_dataset
from app.risk.fraud_detector import FraudDetector, apply_rule_engine, initial_risk_band


def _df():
    rows = generate_dataset(n_accounts=40, avg_txns_per_account=6)
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def test_isolation_forest_scores_in_range():
    df = _df()
    detector = FraudDetector().fit(df)
    scores = detector.score(df)
    assert scores.min() >= 0.0
    assert scores.max() <= 1.0
    assert len(scores) == len(df)


def test_rule_engine_flags_large_amount():
    df = _df()
    row = df.iloc[0].copy()
    row["amount"] = row["account_balance_before"] * 0.95
    reasons = apply_rule_engine(row, df.iloc[1:5])
    assert any("exceeds" in r for r in reasons)


def test_initial_risk_band_monotonic():
    assert initial_risk_band(0.9, 3) in ("HIGH", "CRITICAL")
    assert initial_risk_band(0.05, 0) == "LOW"
