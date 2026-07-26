"""Automated data profiling per kolom (F2)."""
from __future__ import annotations
import re

import pandas as pd


def infer_type(series: pd.Series) -> str:
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    sample = series.dropna().astype(str).head(2000)
    if sample.empty:
        return "text"
    try:
        parsed = pd.to_datetime(sample, errors="coerce", format="mixed", dayfirst=True)
    except (TypeError, ValueError):
        parsed = pd.to_datetime(sample, errors="coerce", dayfirst=True)
    if parsed.notna().mean() > 0.8:
        return "date"
    return "text"


def _pattern_signature(value: str) -> str:
    sig = re.sub(r"[0-9]+", "9", str(value))
    sig = re.sub(r"[A-Za-z]+", "a", sig)
    sig = re.sub(r"(a( a)+)", "a+", sig)  # jumlah kata tidak dihitung sebagai beda format
    return sig[:40]


def pattern_consistency(series: pd.Series) -> float | None:
    """Porsi nilai yang mengikuti pola format dominan pada kolom (proxy dimensi consistency)."""
    sample = series.dropna().astype(str).head(5000)
    if len(sample) < 5:
        return None
    sigs = sample.map(_pattern_signature)
    return float(sigs.value_counts().iloc[0] / len(sigs))


def _display_series(series: pd.Series) -> pd.Series:
    """Representasi teks untuk tampilan (top_values dsb). Kolom ID numerik tanpa desimal
    (NIK, kode) ditulis tanpa akhiran '.0' yang muncul akibat dtype float saat ada nilai
    kosong di kolom."""
    non_null = series.dropna()
    if pd.api.types.is_float_dtype(series) and len(non_null) and (non_null % 1 == 0).all():
        return series.astype("Int64").astype(str)
    return series.astype(str)


def _note_for(name: str, col_type: str, completeness: float, uniqueness: float | None,
              consistency: float | None) -> str:
    notes = []
    if completeness < 0.9:
        notes.append(f"{round((1 - completeness) * 100)}% nilai kosong")
    if consistency is not None and consistency < 0.85 and col_type == "text":
        notes.append("format tidak seragam, perlu standardisasi")
    low = name.lower()
    if uniqueness is not None and uniqueness < 0.9 and any(h in low for h in ("nama", "name")):
        notes.append("kemungkinan variasi ejaan / duplikat")
    return "; ".join(notes)


def profile_dataframe(df: pd.DataFrame) -> list[dict]:
    """Kembalikan profil per kolom untuk disimpan ke tabel dataset_columns."""
    n = len(df)
    profiles = []
    for pos, col in enumerate(df.columns):
        series = df[col]
        non_null = int(series.notna().sum())
        completeness = non_null / n if n else 0.0
        unique_count = int(series.nunique(dropna=True))
        uniqueness = unique_count / non_null if non_null else None
        col_type = infer_type(series)
        consistency = pattern_consistency(series) if col_type == "text" else None

        top = _display_series(series).dropna().value_counts().head(5)
        top_values = [{"value": v, "count": int(c)} for v, c in top.items()]

        stats: dict = {}
        if col_type == "numeric":
            numeric = pd.to_numeric(series, errors="coerce")
            if numeric.notna().any():
                std = numeric.std()
                stats = {
                    "min": float(numeric.min()),
                    "max": float(numeric.max()),
                    "mean": round(float(numeric.mean()), 4),
                    # std() NaN untuk kolom dengan <2 nilai valid — NaN bukan JSON valid
                    "std": round(float(std), 4) if pd.notna(std) else 0.0,
                }
        elif col_type == "date":
            try:
                parsed = pd.to_datetime(series.dropna().astype(str), errors="coerce",
                                        format="mixed", dayfirst=True)
            except (TypeError, ValueError):
                parsed = pd.to_datetime(series.dropna().astype(str), errors="coerce", dayfirst=True)
            if parsed.notna().any():
                stats = {"min": str(parsed.min().date()), "max": str(parsed.max().date())}

        profiles.append({
            "name": str(col),
            "position": pos,
            "inferred_type": col_type,
            "completeness": round(completeness, 4),
            "uniqueness": round(uniqueness, 4) if uniqueness is not None else None,
            "consistency": round(consistency, 4) if consistency is not None else None,
            "null_count": n - non_null,
            "unique_count": unique_count,
            "top_values": top_values,
            "stats": stats,
            "notes": _note_for(str(col), col_type, completeness, uniqueness, consistency),
        })
    return profiles
