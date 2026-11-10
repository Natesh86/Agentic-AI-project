"""
SoloBiz AI - Golden Dataset Loader
Loads test cases T011-T020 from sample_data/golden_mine.csv
"""
import csv
from pathlib import Path
from typing import List, Dict, Any
from config import BASE_DIR


def load_golden_dataset() -> List[Dict[str, Any]]:
    csv_path = BASE_DIR / "sample_data" / "golden_mine.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Golden dataset CSV not found at {csv_path}")

    cases = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cases.append({
                "golden_id": row["golden_id"],
                "ticket_id": row["ticket_id"],
                "input_text": row["input_text"],
                "expected_classification": row["expected_classification"],
                "expected_action": row["expected_action"],
                "expected_output": row["expected_output"],
                "min_confidence": float(row.get("min_confidence", 0.80)),
                "injection_detected": row.get("injection_detected", "false").lower() == "true",
                "hitl_required": row.get("hitl_required", "false").lower() == "true",
                "edge_case_type": row["edge_case_type"],
                "why_it_is_in_the_set": row["why_it_is_in_the_set"]
            })
    return cases
