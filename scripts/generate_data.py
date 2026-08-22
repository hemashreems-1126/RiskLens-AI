"""Standalone helper: regenerate data/synthetic_transactions.json without
starting the full backend. Run from the backend/ directory:
    python ../scripts/generate_data.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from app.services.data_generator import generate_dataset
import json

if __name__ == "__main__":
    data = generate_dataset()
    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic_transactions.json")
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {len(data)} synthetic transactions to {out_path}")
