"""Standardization & parsing (backlog #4): normalisasi HP, email, nama, alamat, tanggal.

Transformasi bersifat konservatif — nilai yang tidak bisa dinormalisasi dibiarkan apa adanya,
tidak pernah dikosongkan.
"""
from __future__ import annotations

import re

import pandas as pd

from .entity_resolution import detect_roles
from .profiling import infer_type
from .rule_engine import normalize_phone

MAX_SAMPLES = 5

# canonicalisasi penulisan alamat Indonesia yang umum
_ADDRESS_PATTERNS = [
    (re.compile(r"\b(?:jl|jln|jalan)\.?\s+", re.IGNORECASE), "Jl. "),
    (re.compile(r"\b(?:no|nomor)\.?\s*(?=\d)", re.IGNORECASE), "No. "),
    (re.compile(r"\brt\.?\s*(?=\d)", re.IGNORECASE), "RT "),
    (re.compile(r"\brw\.?\s*(?=\d)", re.IGNORECASE), "RW "),
]


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _title_case(text: str) -> str:
    return " ".join(w.capitalize() if not w.isupper() or len(w) > 3 else w
                    for w in text.split())


def _std_phone(value: str) -> str:
    normalized = normalize_phone(value)
    return normalized if normalized else value


def _std_email(value: str) -> str:
    return _collapse(value).lower()


def _std_name(value: str) -> str:
    return _title_case(_collapse(value))


def _std_address(value: str) -> str:
    text = _collapse(value)
    for pattern, replacement in _ADDRESS_PATTERNS:
        text = pattern.sub(replacement, text)
    return _title_case(text)


def _std_date(value: str) -> str:
    parsed = pd.to_datetime(str(value).strip(), errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        return value
    return parsed.strftime("%Y-%m-%d")


def _std_text(value: str) -> str:
    return _collapse(value)


def standardize_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Kembalikan (df_baru, report). Report per kolom yang tersentuh:
    {column, kind, changed, samples: [{row, before, after}]}."""
    roles = detect_roles([str(c) for c in df.columns])
    role_by_column = {col: role for role, col in roles.items()}

    out = df.copy()
    report: list[dict] = []
    for col in df.columns:
        series = df[col]
        if pd.api.types.is_numeric_dtype(series):
            # kolom ID (NIK dsb) yang terbaca float ditulis ulang tanpa ".0"
            if pd.api.types.is_float_dtype(series):
                non_null = series.dropna()
                if len(non_null) and (non_null % 1 == 0).all():
                    out[col] = series.astype("Int64")
            continue
        role = role_by_column.get(str(col))
        if role == "phone":
            kind, fn = "nomor_hp", _std_phone
        elif role == "email":
            kind, fn = "email", _std_email
        elif role == "name":
            kind, fn = "nama", _std_name
        elif role == "address":
            kind, fn = "alamat", _std_address
        elif infer_type(series) == "date":
            kind, fn = "tanggal_iso", _std_date
        else:
            kind, fn = "teks", _std_text

        changed = 0
        samples: list[dict] = []
        new_values = series.copy()
        for idx, value in series.items():
            if value is None or (isinstance(value, float) and pd.isna(value)):
                continue
            before = str(value)
            after = fn(before)
            if after != before:
                changed += 1
                new_values.at[idx] = after
                if len(samples) < MAX_SAMPLES:
                    samples.append({"row": int(idx), "before": before, "after": after})
        if changed:
            out[col] = new_values
            report.append({"column": str(col), "kind": kind,
                           "changed": changed, "samples": samples})
    return out, report
