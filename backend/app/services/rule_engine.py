"""Rule engine dasar (F3): rule bawaan format Indonesia + rentang nilai."""
from __future__ import annotations
import re

import pandas as pd

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
NIK_RE = re.compile(r"^\d{16}$")
PHONE_ID_RE = re.compile(r"^08\d{8,11}$")

RULE_TYPES = {
    "email_format": "Format email valid",
    "phone_id": "Nomor HP Indonesia (10-13 digit, awalan 08 / +62)",
    "nik": "NIK 16 digit numerik",
    "not_null": "Tidak boleh kosong",
    "numeric_range": "Angka dalam rentang",
    "date_range": "Tanggal dalam rentang wajar",
    "regex": "Pola regex kustom",
    "cross_column": "Perbandingan antar kolom (mis. checkout > checkin)",
}

CROSS_OPS = {
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def _comparable(value):
    """Konversi nilai ke tipe yang bisa dibandingkan: angka, tanggal, atau teks."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if text == "":
        return None
    try:
        return float(text.replace(",", "."))
    except ValueError:
        pass
    parsed = pd.to_datetime(text, errors="coerce", dayfirst=True)
    if not pd.isna(parsed):
        return parsed
    return text.lower()


def run_cross_column_rule(df: pd.DataFrame, params: dict) -> dict:
    """Rule lintas kolom: params {left, op, right}. Baris dengan nilai tak
    terbandingkan (kosong/beda tipe) dilewati, bukan dihitung pelanggaran."""
    left_col, right_col = params.get("left"), params.get("right")
    op = CROSS_OPS.get(params.get("op", ""))
    if not left_col or not right_col or op is None \
            or left_col not in df.columns or right_col not in df.columns:
        return {"checked": 0, "violations": 0, "samples": []}
    checked = violations = 0
    samples: list[dict] = []
    for idx in df.index:
        left = _comparable(df.at[idx, left_col])
        right = _comparable(df.at[idx, right_col])
        if left is None or right is None or type(left) is not type(right):
            continue
        checked += 1
        try:
            ok = op(left, right)
        except TypeError:
            continue
        if not ok:
            violations += 1
            if len(samples) < 10:
                samples.append({"row": int(idx),
                                "value": f"{left_col}={df.at[idx, left_col]} vs "
                                         f"{right_col}={df.at[idx, right_col]}"})
    return {"checked": checked, "violations": violations, "samples": samples}


def normalize_phone(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    digits = re.sub(r"\D", "", str(value))
    if digits.startswith("620"):
        digits = digits[2:]
    elif digits.startswith("62"):
        digits = "0" + digits[2:]
    elif digits.startswith("8") and len(digits) >= 9:
        # leading 0 sering hilang saat data lewat Excel
        digits = "0" + digits
    return digits


def _check_value(rule_type: str, params: dict, value) -> bool:
    """True = valid."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        # nilai kosong hanya dilanggar oleh rule not_null
        return rule_type != "not_null"
    if isinstance(value, float) and value.is_integer():
        # kolom ID numerik (NIK, no HP) sering terbaca float oleh pandas
        value = int(value)
    text = str(value).strip()
    if text == "":
        return rule_type != "not_null"

    if rule_type == "not_null":
        return True
    if rule_type == "email_format":
        return bool(EMAIL_RE.match(text.lower()))
    if rule_type == "phone_id":
        return bool(PHONE_ID_RE.match(normalize_phone(text)))
    if rule_type == "nik":
        return bool(NIK_RE.match(re.sub(r"\D", "", text)))
    if rule_type == "regex":
        try:
            return bool(re.match(params.get("pattern", ".*"), text))
        except re.error:
            return True
    if rule_type == "numeric_range":
        try:
            num = float(text.replace(",", "."))
        except ValueError:
            return False
        lo, hi = params.get("min"), params.get("max")
        if lo is not None and num < float(lo):
            return False
        if hi is not None and num > float(hi):
            return False
        return True
    if rule_type == "date_range":
        parsed = pd.to_datetime(text, errors="coerce", dayfirst=True)
        if pd.isna(parsed):
            return False
        lo, hi = params.get("min"), params.get("max")
        if lo and parsed < pd.to_datetime(lo):
            return False
        if hi and parsed > pd.to_datetime(hi):
            return False
        return True
    return True


def run_rule(df: pd.DataFrame, column: str, rule_type: str, params: dict | None) -> dict:
    params = params or {}
    if rule_type == "cross_column":
        return run_cross_column_rule(df, params)
    if column not in df.columns:
        return {"checked": 0, "violations": 0, "samples": []}
    series = df[column]
    checked = len(series)
    samples: list[dict] = []
    violations = 0
    for idx, value in series.items():
        if not _check_value(rule_type, params, value):
            violations += 1
            if len(samples) < 10:
                display = value
                if isinstance(display, float) and not pd.isna(display) and display.is_integer():
                    display = int(display)
                samples.append({"row": int(idx), "value": None if pd.isna(value) else str(display)})
    return {"checked": checked, "violations": violations, "samples": samples}


def suggest_builtin_rules(df: pd.DataFrame, profiles: list[dict]) -> list[dict]:
    """Auto-attach rule bawaan berdasar heuristik nama kolom & tipe."""
    suggestions = []
    for prof in profiles:
        name = prof["name"]
        low = name.lower()
        if "email" in low or "mail" in low:
            suggestions.append({"column_name": name, "rule_type": "email_format",
                                "params": {}, "description": RULE_TYPES["email_format"]})
        elif "nik" in low or "ktp" in low:
            suggestions.append({"column_name": name, "rule_type": "nik",
                                "params": {}, "description": RULE_TYPES["nik"]})
        elif any(h in low for h in ("hp", "phone", "telp", "telepon", "handphone", "msisdn")):
            suggestions.append({"column_name": name, "rule_type": "phone_id",
                                "params": {}, "description": RULE_TYPES["phone_id"]})
        elif prof["inferred_type"] == "date" and any(h in low for h in ("lahir", "birth")):
            suggestions.append({
                "column_name": name, "rule_type": "date_range",
                "params": {"min": "1900-01-01", "max": "2026-12-31"},
                "description": "Tanggal lahir dalam rentang wajar (1900 - sekarang)",
            })
    return suggestions
