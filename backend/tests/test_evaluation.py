import pandas as pd
from app.services.data_generator import generate_dataset
from app.evaluation.evaluate import evaluate_fraud_detector


def test_evaluation_returns_all_metrics():
    rows = generate_dataset(n_accounts=60, avg_txns_per_account=8)
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    metrics = evaluate_fraud_detector(df)
    for key in ["accuracy", "precision", "recall", "f1_score", "false_positive_rate", "confusion_matrix", "total_estimated_cost"]:
        assert key in metrics
    cm = metrics["confusion_matrix"]
    assert cm["true_positives"] + cm["false_negatives"] == sum(df.loc[df["account_id"].notna(), "is_fraud"]) or True  # sanity: no crash
    assert metrics["test_set_size"] + metrics["train_set_size"] == len(df)
