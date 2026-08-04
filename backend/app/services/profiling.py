"""Structure, content, and key-oriented discovery for dataset columns."""
from __future__ import annotations

import re

import pandas as pd


PROFILE_SAMPLE_SIZE = 5000
MAX_DISTRIBUTION_ITEMS = 10


def _missing_mask(series: pd.Series) -> pd.Series:
    """Treat NULL and whitespace-only strings as missing values."""
    mask = series.isna()
    if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
        mask = mask | series.fillna("").astype(str).str.strip().eq("")
    return mask


def _present_values(series: pd.Series) -> pd.Series:
    return series.loc[~_missing_mask(series)]


def infer_type(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"

    sample = _present_values(series).astype(str).head(2000)
    if sample.empty:
        return "text"

    normalized = sample.str.strip().str.lower()
    if normalized.isin({"true", "false", "yes", "no", "ya", "tidak"}).all():
        return "boolean"

    numeric = pd.to_numeric(sample, errors="coerce")
    if numeric.notna().mean() > 0.8:
        return "numeric"

    try:
        parsed = pd.to_datetime(sample, errors="coerce", format="mixed", dayfirst=True)
    except (TypeError, ValueError):
        parsed = pd.to_datetime(sample, errors="coerce", dayfirst=True)
    if parsed.notna().mean() > 0.8:
        return "date"
    return "text"


def _pattern_signature(value: str) -> str:
    """Human-readable shape used to group values with the same format."""
    signature = re.sub(r"[0-9]+", "9", str(value))
    signature = re.sub(r"[A-Z]+", "A", signature)
    signature = re.sub(r"[a-z]+", "a", signature)
    return signature[:80]


def _regex_for(value: str) -> str:
    """Create an anchored regex for the character-run shape of one value."""
    parts: list[str] = []
    index = 0
    text = str(value)
    while index < len(text):
        char = text[index]
        if char.isdigit():
            token = r"\d"
            predicate = str.isdigit
        elif char.isalpha() and char.isupper():
            token = "[A-Z]"
            predicate = lambda item: item.isalpha() and item.isupper()
        elif char.isalpha():
            token = "[a-z]"
            predicate = lambda item: item.isalpha() and item.islower()
        elif char.isspace():
            token = r"\s"
            predicate = str.isspace
        else:
            parts.append(re.escape(char))
            index += 1
            continue

        end = index + 1
        while end < len(text) and predicate(text[end]):
            end += 1
        length = end - index
        parts.append(f"{token}{{{length}}}")
        index = end
    return "^" + "".join(parts) + "$"


def pattern_distribution(series: pd.Series) -> list[dict]:
    sample = _present_values(series).astype(str).head(PROFILE_SAMPLE_SIZE)
    if sample.empty:
        return []
    grouped: dict[str, dict] = {}
    for value in sample:
        regex = _regex_for(value)
        item = grouped.setdefault(regex, {
            "regex": regex,
            "signature": _pattern_signature(value),
            "count": 0,
            "example": value[:100],
        })
        item["count"] += 1
    ranked = sorted(grouped.values(), key=lambda item: (-item["count"], item["regex"]))
    for item in ranked:
        item["percentage"] = round(item["count"] / len(sample), 4)
    return ranked[:MAX_DISTRIBUTION_ITEMS]


def pattern_consistency(series: pd.Series) -> float | None:
    """Share of values following the dominant format pattern."""
    patterns = pattern_distribution(series)
    sample_count = min(len(_present_values(series)), PROFILE_SAMPLE_SIZE)
    if sample_count < 5 or not patterns:
        return None
    return float(patterns[0]["count"] / sample_count)


def _display_values(series: pd.Series) -> pd.Series:
    """Keep identifiers readable, including integral values stored as floats."""
    values = _present_values(series)
    if pd.api.types.is_float_dtype(series) and len(values) and (values % 1 == 0).all():
        return values.astype("Int64").astype(str)
    return values.astype(str)


def _length_stats(series: pd.Series) -> dict:
    lengths = _display_values(series).str.len()
    if lengths.empty:
        return {"min": None, "max": None, "mean": None, "median": None}
    return {
        "min": int(lengths.min()),
        "max": int(lengths.max()),
        "mean": round(float(lengths.mean()), 2),
        "median": round(float(lengths.median()), 2),
    }


def _note_for(name: str, col_type: str, completeness: float, uniqueness: float | None,
              consistency: float | None) -> str:
    notes = []
    if completeness < 0.9:
        notes.append(f"{round((1 - completeness) * 100)}% nilai kosong")
    if consistency is not None and consistency < 0.85 and col_type == "text":
        notes.append("format tidak seragam, perlu standardisasi")
    if uniqueness is not None and uniqueness < 0.9 and any(
        hint in name.lower() for hint in ("nama", "name")
    ):
        notes.append("kemungkinan variasi ejaan / duplikat")
    return "; ".join(notes)


def _content_stats(series: pd.Series, col_type: str) -> dict:
    stats: dict = {
        "physical_type": str(series.dtype),
        "length": _length_stats(series),
    }
    present = _present_values(series)
    if col_type == "numeric":
        numeric = pd.to_numeric(present, errors="coerce").dropna()
        if not numeric.empty:
            std = numeric.std()
            stats.update({
                "min": float(numeric.min()),
                "max": float(numeric.max()),
                "mean": round(float(numeric.mean()), 4),
                "median": round(float(numeric.median()), 4),
                "std": round(float(std), 4) if pd.notna(std) else 0.0,
                "q1": round(float(numeric.quantile(0.25)), 4),
                "q3": round(float(numeric.quantile(0.75)), 4),
            })
    elif col_type == "date":
        try:
            parsed = pd.to_datetime(present.astype(str), errors="coerce",
                                    format="mixed", dayfirst=True).dropna()
        except (TypeError, ValueError):
            parsed = pd.to_datetime(present.astype(str), errors="coerce",
                                    dayfirst=True).dropna()
        if not parsed.empty:
            stats.update({"min": str(parsed.min().date()), "max": str(parsed.max().date())})
    if col_type == "text":
        stats["patterns"] = pattern_distribution(series)
    return stats


def profile_dataframe(df: pd.DataFrame) -> list[dict]:
    """Return a backward-compatible, thorough profile for every dataframe column."""
    row_count = len(df)
    profiles = []
    for position, column in enumerate(df.columns):
        series = df[column]
        missing = _missing_mask(series)
        non_missing = int((~missing).sum())
        null_count = int(series.isna().sum())
        blank_count = int((missing & series.notna()).sum())
        completeness = non_missing / row_count if row_count else 0.0
        present = _present_values(series)
        unique_count = int(present.nunique(dropna=True))
        uniqueness = unique_count / non_missing if non_missing else None
        duplicate_count = non_missing - unique_count
        col_type = infer_type(series)
        consistency = pattern_consistency(series) if col_type == "text" else None

        top = _display_values(series).value_counts().head(MAX_DISTRIBUTION_ITEMS)
        top_values = [
            {"value": value, "count": int(count),
             "percentage": round(int(count) / non_missing, 4)}
            for value, count in top.items()
        ] if non_missing else []

        stats = _content_stats(series, col_type)
        stats.update({
            "null_count": null_count,
            "blank_count": blank_count,
            "non_missing_count": non_missing,
            "duplicate_count": duplicate_count,
            "is_candidate_key": bool(row_count and non_missing == row_count and duplicate_count == 0),
            "frequency_count": len(top_values),
        })

        profiles.append({
            "name": str(column),
            "position": position,
            "inferred_type": col_type,
            "completeness": round(completeness, 4),
            "uniqueness": round(uniqueness, 4) if uniqueness is not None else None,
            "consistency": round(consistency, 4) if consistency is not None else None,
            "null_count": null_count + blank_count,
            "unique_count": unique_count,
            "top_values": top_values,
            "stats": stats,
            "notes": _note_for(str(column), col_type, completeness, uniqueness, consistency),
        })
    return profiles
