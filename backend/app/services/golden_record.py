"""Golden record builder (F7) dengan survivorship rule configurable per kolom.

Strategi: latest_update (default bila ada kolom tanggal update), first_non_null,
most_frequent, longest, source_priority. Konfigurasi per dataset disimpan di
datasets.survivorship_config = {column: {strategy, params}}.
"""
from __future__ import annotations

from collections import Counter

import pandas as pd

from .entity_resolution import detect_roles

STRATEGY_LABELS = {
    "latest_update": "Update Terbaru",
    "first_non_null": "Non-Kosong Pertama",
    "most_frequent": "Nilai Tersering",
    "longest": "Nilai Terpanjang",
    "source_priority": "Prioritas Sumber",
}


def _parse_date(value):
    if value in (None, ""):
        return None
    parsed = pd.to_datetime(str(value), errors="coerce", dayfirst=True)
    return None if pd.isna(parsed) else parsed


def _is_empty(value) -> bool:
    return value is None or str(value).strip() == ""


def _pick(members: list[dict], col: str):
    """Kembalikan (value, record_index) non-kosong pertama sesuai urutan members."""
    for member in members:
        value = member["record_data"].get(col)
        if not _is_empty(value):
            return value, member["record_index"]
    return None, None


def build_golden(members: list[dict], config: dict | None = None) -> tuple[dict, dict]:
    """members: [{record_index, record_data}] -> (golden_data, provenance)."""
    config = config or {}
    columns: list[str] = []
    for member in members:
        for col in member["record_data"].keys():
            if col not in columns:
                columns.append(col)

    roles = detect_roles(columns)
    updated_col = roles.get("updated")
    source_col = roles.get("source")
    default_strategy = "latest_update" if updated_col else "first_non_null"

    def latest_key(member: dict):
        if updated_col:
            parsed = _parse_date(member["record_data"].get(updated_col))
            if parsed is not None:
                return parsed
        return pd.Timestamp.min

    by_latest = sorted(members, key=latest_key, reverse=True)

    golden: dict = {}
    provenance: dict = {}
    for col in columns:
        col_cfg = config.get(col) or {}
        strategy = col_cfg.get("strategy") or default_strategy
        if strategy not in STRATEGY_LABELS:
            strategy = default_strategy
        params = col_cfg.get("params") or {}

        non_empty = [(m["record_data"].get(col), m["record_index"])
                     for m in members if not _is_empty(m["record_data"].get(col))]
        distinct = {str(v) for v, _ in non_empty}

        # semua record sepakat -> tidak perlu strategi
        if len(distinct) == 1 and len(non_empty) == len(members):
            golden[col] = non_empty[0][0]
            provenance[col] = {"record_index": non_empty[0][1], "rule": "same_in_all"}
            continue

        if not non_empty:
            golden[col] = None
            provenance[col] = {"record_index": None, "rule": strategy}
            continue

        if strategy == "latest_update":
            value, source = _pick(by_latest, col)
        elif strategy == "first_non_null":
            value, source = _pick(members, col)
        elif strategy == "most_frequent":
            counts = Counter(str(v) for v, _ in non_empty)
            winner = counts.most_common(1)[0][0]
            value, source = next((v, idx) for v, idx in non_empty if str(v) == winner)
        elif strategy == "longest":
            value, source = max(non_empty, key=lambda pair: len(str(pair[0])))
        elif strategy == "source_priority":
            priority = [str(p).strip().lower() for p in params.get("priority", [])]

            def prio_key(member: dict):
                src = str(member["record_data"].get(source_col, "")).strip().lower() \
                    if source_col else ""
                rank = priority.index(src) if src in priority else len(priority)
                return (rank, -latest_key(member).value)

            value, source = _pick(sorted(members, key=prio_key), col)
        else:  # pragma: no cover
            value, source = _pick(members, col)

        golden[col] = value
        provenance[col] = {"record_index": source, "rule": strategy}
    return golden, provenance
