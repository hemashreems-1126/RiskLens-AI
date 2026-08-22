from app.services.data_generator import generate_dataset


def test_generate_dataset_has_both_classes():
    rows = generate_dataset(n_accounts=40, avg_txns_per_account=6)
    assert len(rows) > 0
    fraud = [r for r in rows if r["is_fraud"]]
    normal = [r for r in rows if not r["is_fraud"]]
    assert len(fraud) > 0
    assert len(normal) > 0


def test_generated_rows_have_required_fields():
    rows = generate_dataset(n_accounts=10, avg_txns_per_account=3)
    required = {
        "transaction_id", "account_id", "merchant_id", "timestamp", "amount",
        "currency", "transaction_type", "payment_method", "sender", "receiver",
        "account_balance_before", "account_balance_after", "location",
        "device_id", "ip_address", "transaction_status", "is_fraud",
    }
    assert required.issubset(rows[0].keys())
