"""Anomaly/outlier detection (F8): IQR fence + z-score untuk kolom numerik.

Penjelasan root-cause berbasis LLM adalah enhancement terpisah (backlog #21).
"""
from __future__ import annotations

import pandas as pd

# kolom identitas: nilai numeriknya bukan besaran, outlier tidak bermakna
ID_HINTS = ("nik", "ktp", "hp", "phone", "telp", "kode", "npwp")
MAX_PER_COLUMN = 20


def _is_identifier_column(name: str) -> bool:
    low = name.lower()
    if low == "id" or low.endswith("_id") or low.startswith("id_"):
        return True
    return any(h in low for h in ID_HINTS)


def detect_anomalies(df: pd.DataFrame, profiles: list[dict]) -> list[dict]:
    anomalies: list[dict] = []
    for prof in profiles:
        name = prof["name"]
        if prof["inferred_type"] != "numeric" or _is_identifier_column(name):
            continue
        series = pd.to_numeric(df[name], errors="coerce").dropna()
        if len(series) < 8 or series.nunique() < 3:
            continue

        q1, q3 = float(series.quantile(0.25)), float(series.quantile(0.75))
        iqr = q3 - q1
        std_raw = series.std()
        std = float(std_raw) if pd.notna(std_raw) else 0.0
        mean = float(series.mean())
        if iqr == 0 and std == 0:
            continue
        lo_fence, hi_fence = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        lo_extreme, hi_extreme = q1 - 3 * iqr, q3 + 3 * iqr

        count = 0
        for idx, value in series.items():
            v = float(value)
            z = (v - mean) / std if std else 0.0
            outlier_iqr = iqr > 0 and (v < lo_fence or v > hi_fence)
            outlier_z = abs(z) > 3
            if not outlier_iqr and not outlier_z:
                continue
            extreme = (iqr > 0 and (v < lo_extreme or v > hi_extreme)) or abs(z) > 4
            arah = "di atas" if v > mean else "di bawah"
            anomalies.append({
                "column_name": name,
                "record_index": int(idx),
                "anomaly_type": "outlier_iqr" if outlier_iqr else "outlier_zscore",
                "value": str(value),
                "explanation": (
                    f"Nilai {value:g} jauh {arah} rentang tipikal kolom "
                    f"({q1:g}–{q3:g}); z-score {z:.1f}. Kemungkinan salah input, "
                    f"salah satuan, atau memang kejadian ekstrem — perlu dicek manual."
                ),
                "severity": "tinggi" if extreme else "sedang",
            })
            count += 1
            if count >= MAX_PER_COLUMN:
                break
    return anomalies
