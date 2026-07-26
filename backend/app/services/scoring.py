"""Skor kualitas 0-100 per dimensi: completeness, validity, uniqueness, consistency."""
from __future__ import annotations


def compute_dimensions(profiles: list[dict], rule_results: list[dict],
                       duplicate_records: int, total_rows: int) -> dict:
    dims: dict[str, float] = {}

    if profiles:
        dims["completeness"] = sum(p["completeness"] for p in profiles) / len(profiles)

    consistencies = [p["consistency"] for p in profiles if p.get("consistency") is not None]
    if consistencies:
        dims["consistency"] = sum(consistencies) / len(consistencies)

    total_checked = sum(r["checked"] for r in rule_results)
    if total_checked:
        total_violations = sum(r["violations"] for r in rule_results)
        dims["validity"] = 1 - (total_violations / total_checked)

    if total_rows:
        dims["uniqueness"] = 1 - (duplicate_records / total_rows)

    overall = round(100 * (sum(dims.values()) / len(dims)), 1) if dims else None
    return {
        "overall": overall,
        "dimensions": {k: round(v * 100, 1) for k, v in dims.items()},
    }
