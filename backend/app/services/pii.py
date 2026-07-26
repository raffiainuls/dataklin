"""PII Detection & Masking (F11): deteksi kolom sensitif otomatis + rekomendasi masking.

Deteksi berbasis pola konten (regex) + heuristik nama kolom — bukan NER (model ML
terpisah), konsisten dengan pendekatan rule-based di seluruh codebase ini. Cukup untuk
menandai kandidat PII yang jelas (NIK, HP, email, nama, alamat); kasus ambigu tetap perlu
ditinjau manusia, sama seperti rule engine & entity resolution.
"""
from __future__ import annotations

import hashlib
import re

import pandas as pd

PII_LABELS = {
    "nik": "NIK",
    "phone": "Nomor HP",
    "email": "Email",
    "name": "Nama",
    "address": "Alamat",
}

_NIK_CONTENT_RE = re.compile(r"^\d{16}$")
_EMAIL_CONTENT_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_CONTENT_RE = re.compile(r"^(\+?62|0)8\d{7,11}$")
_NAME_HINTS = ("nama", "name")
_ADDRESS_HINTS = ("alamat", "address", "addr")

CONTENT_MATCH_THRESHOLD = 0.6


def recommend_masking(pii_type: str) -> dict:
    if pii_type in ("nik", "phone"):
        return {"strategy": "partial", "params": {"keep_start": 4, "keep_end": 2}}
    if pii_type == "email":
        return {"strategy": "email_mask", "params": {}}
    return {"strategy": "hash", "params": {}}


def detect_pii(df: pd.DataFrame, roles: dict) -> list[dict]:
    """roles: hasil entity_resolution.detect_roles(df.columns) — dipakai sebagai sinyal
    tambahan di samping deteksi konten & nama kolom sendiri."""
    role_by_column = {col: role for role, col in roles.items()}
    findings = []
    for col in df.columns:
        col_name = str(col)
        non_null = df[col].dropna()
        if non_null.empty:
            continue
        # kolom ID numerik (NIK dsb) tidak boleh tampil sebagai "...001.0"
        if pd.api.types.is_float_dtype(non_null) and (non_null % 1 == 0).all():
            non_null = non_null.astype("Int64")
        sample = non_null.astype(str).head(200)
        low = col_name.lower()
        role = role_by_column.get(col_name)

        pii_type = None
        if role == "phone" or sample.map(
                lambda v: bool(_PHONE_CONTENT_RE.match(re.sub(r"[\s\-()]", "", v)))
        ).mean() > CONTENT_MATCH_THRESHOLD:
            pii_type = "phone"
        elif role == "email" or sample.map(
                lambda v: bool(_EMAIL_CONTENT_RE.match(v))).mean() > CONTENT_MATCH_THRESHOLD:
            pii_type = "email"
        elif "nik" in low or "ktp" in low or sample.map(
                lambda v: bool(_NIK_CONTENT_RE.match(re.sub(r"\D", "", v)))
        ).mean() > CONTENT_MATCH_THRESHOLD:
            pii_type = "nik"
        elif role == "name" or any(h in low for h in _NAME_HINTS):
            pii_type = "name"
        elif role == "address" or any(h in low for h in _ADDRESS_HINTS):
            pii_type = "address"

        if pii_type:
            masking = recommend_masking(pii_type)
            findings.append({
                "column_name": col_name,
                "pii_type": pii_type,
                "pii_label": PII_LABELS[pii_type],
                "masking": masking,
                "sample_masked": apply_mask(sample.iloc[0], masking["strategy"],
                                            masking["params"]),
            })
    return findings


def apply_mask(value, strategy: str, params: dict) -> str:
    # Series.map() pada kolom Int64 nullable mengonversi elemen ke Python float
    # (kuirk pandas) — kolom ID numerik (NIK dsb) tidak boleh tampil sebagai "...001.0"
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value)
    if strategy == "partial":
        keep_start, keep_end = params.get("keep_start", 3), params.get("keep_end", 2)
        if len(text) <= keep_start + keep_end:
            return "*" * len(text)
        return text[:keep_start] + "*" * (len(text) - keep_start - keep_end) + text[-keep_end:]
    if strategy == "email_mask":
        if "@" not in text:
            return "*" * len(text)
        local, domain = text.split("@", 1)
        visible = local[:2]
        return f"{visible}{'*' * max(len(local) - len(visible), 1)}@{domain}"
    if strategy == "hash":
        return hashlib.sha256(text.encode()).hexdigest()[:12]
    return text


def mask_dataframe(df: pd.DataFrame, findings: list[dict]) -> pd.DataFrame:
    out = df.copy()
    for finding in findings:
        col = finding["column_name"]
        if col not in out.columns:
            continue
        strategy, params = finding["masking"]["strategy"], finding["masking"]["params"]
        out[col] = out[col].map(
            lambda v: None if v is None or (isinstance(v, float) and pd.isna(v))
            else apply_mask(v, strategy, params)
        )
    return out
