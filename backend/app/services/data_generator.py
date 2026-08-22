"""
Synthetic payment transaction dataset generator.

ALL data produced here is synthetic. No real Razorpay data, no real
customer data, no real payment data is used anywhere in this project.

The generator deliberately injects realistic fraud-like patterns
(unusual amount, velocity bursts, device/IP changes, balance drains,
repeated receivers, odd locations) so the downstream fraud detector
and agents have real signal to work with.
"""
from __future__ import annotations
import random
import uuid
import datetime as dt
from dataclasses import dataclass, asdict

random.seed(42)

LOCATIONS = ["Bengaluru", "Mumbai", "Delhi", "Chennai", "Hyderabad", "Pune", "Kolkata", "Jaipur"]
RARE_LOCATIONS = ["Lagos", "Manila", "Bucharest", "Karachi"]
PAYMENT_METHODS = ["UPI", "credit_card", "debit_card", "netbanking", "wallet"]
TXN_TYPES = ["p2p_transfer", "merchant_payment", "bill_payment", "wallet_topup", "refund"]


@dataclass
class SyntheticTransaction:
    transaction_id: str
    account_id: str
    merchant_id: str
    timestamp: str
    amount: float
    currency: str
    transaction_type: str
    payment_method: str
    sender: str
    receiver: str
    account_balance_before: float
    account_balance_after: float
    location: str
    device_id: str
    ip_address: str
    transaction_status: str
    is_fraud: bool


def _rand_account(prefix="ACC"):
    return f"{prefix}{random.randint(10000, 99999)}"


def _rand_device():
    return f"DEV{random.randint(1000, 9999)}"


def _rand_ip():
    return f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"


def _normal_transaction(account_id: str, base_time: dt.datetime, device_id: str, ip: str) -> SyntheticTransaction:
    balance_before = round(random.uniform(2000, 150000), 2)
    amount = round(random.uniform(50, min(15000, balance_before * 0.4)), 2)
    return SyntheticTransaction(
        transaction_id=str(uuid.uuid4()),
        account_id=account_id,
        merchant_id=_rand_account("MER"),
        timestamp=base_time.isoformat(),
        amount=amount,
        currency="INR",
        transaction_type=random.choice(TXN_TYPES),
        payment_method=random.choice(PAYMENT_METHODS),
        sender=account_id,
        receiver=_rand_account("ACC"),
        account_balance_before=balance_before,
        account_balance_after=round(balance_before - amount, 2),
        location=random.choice(LOCATIONS),
        device_id=device_id,
        ip_address=ip,
        transaction_status="completed",
        is_fraud=False,
    )


def _fraud_pattern_burst(account_id: str, base_time: dt.datetime) -> list[SyntheticTransaction]:
    """Rapid, high-value transfers to the same receiver from a new device/IP/location —
    simulates account takeover + balance drain."""
    txns = []
    balance = round(random.uniform(50000, 300000), 2)
    receiver = _rand_account("ACC")
    device_id = _rand_device()
    ip = _rand_ip()
    location = random.choice(RARE_LOCATIONS)
    n = random.randint(3, 6)
    t = base_time
    for i in range(n):
        amount = round(balance * random.uniform(0.2, 0.45), 2)
        amount = min(amount, balance)
        txns.append(SyntheticTransaction(
            transaction_id=str(uuid.uuid4()),
            account_id=account_id,
            merchant_id=_rand_account("MER"),
            timestamp=t.isoformat(),
            amount=amount,
            currency="INR",
            transaction_type="p2p_transfer",
            payment_method="UPI",
            sender=account_id,
            receiver=receiver,
            account_balance_before=balance,
            account_balance_after=round(balance - amount, 2),
            location=location,
            device_id=device_id,
            ip_address=ip,
            transaction_status="completed",
            is_fraud=True,
        ))
        balance = round(balance - amount, 2)
        t = t + dt.timedelta(minutes=random.randint(1, 4))
    return txns


def _fraud_pattern_single_large(account_id: str, base_time: dt.datetime) -> SyntheticTransaction:
    """A single unusually large payment, far outside the account's normal range."""
    balance = round(random.uniform(20000, 80000), 2)
    amount = round(balance * random.uniform(0.85, 1.0), 2)
    return SyntheticTransaction(
        transaction_id=str(uuid.uuid4()),
        account_id=account_id,
        merchant_id=_rand_account("MER"),
        timestamp=base_time.isoformat(),
        amount=amount,
        currency="INR",
        transaction_type="merchant_payment",
        payment_method=random.choice(["credit_card", "UPI"]),
        sender=account_id,
        receiver=_rand_account("ACC"),
        account_balance_before=balance,
        account_balance_after=round(balance - amount, 2),
        location=random.choice(RARE_LOCATIONS),
        device_id=_rand_device(),
        ip_address=_rand_ip(),
        transaction_status="completed",
        is_fraud=True,
    )


def generate_dataset(n_accounts: int = 120, avg_txns_per_account: int = 12, fraud_account_ratio: float = 0.12):
    """Generate a synthetic dataset. Returns a list of dict rows.

    ~fraud_account_ratio of accounts will contain an injected fraud pattern
    (burst or single-large). All other transactions are normal.
    """
    rows: list[SyntheticTransaction] = []
    start = dt.datetime(2026, 1, 1)

    n_fraud_accounts = max(1, int(n_accounts * fraud_account_ratio))
    fraud_accounts = set(random.sample(range(n_accounts), n_fraud_accounts))

    for i in range(n_accounts):
        account_id = _rand_account()
        device_id = _rand_device()
        ip = _rand_ip()
        n_txns = max(1, int(random.gauss(avg_txns_per_account, 4)))
        acct_time = start + dt.timedelta(days=random.randint(0, 200), hours=random.randint(0, 23))

        for _ in range(n_txns):
            acct_time += dt.timedelta(hours=random.randint(1, 48))
            rows.append(_normal_transaction(account_id, acct_time, device_id, ip))

        if i in fraud_accounts:
            acct_time += dt.timedelta(hours=random.randint(1, 24))
            if random.random() < 0.5:
                rows.extend(_fraud_pattern_burst(account_id, acct_time))
            else:
                rows.append(_fraud_pattern_single_large(account_id, acct_time))

    random.shuffle(rows)
    return [asdict(r) for r in rows]


def generate_dataset_for_db(**kwargs) -> list[dict]:
    """Same as generate_dataset but with `timestamp` converted to a real
    datetime object (SQLAlchemy DateTime columns reject ISO strings on
    SQLite, so this conversion must happen before insertion)."""
    rows = generate_dataset(**kwargs)
    for row in rows:
        row["timestamp"] = dt.datetime.fromisoformat(row["timestamp"])
    return rows


if __name__ == "__main__":
    import json
    data = generate_dataset()
    print(f"Generated {len(data)} synthetic transactions, {sum(1 for r in data if r['is_fraud'])} labelled fraud.")
    with open("data/synthetic_transactions.json", "w") as f:
        json.dump(data, f, indent=2)
