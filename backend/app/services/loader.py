"""Ingestion (F1): deteksi otomatis encoding & delimiter, load CSV/XLSX ke DataFrame."""
from __future__ import annotations
import csv
import io
import re

import pandas as pd
from charset_normalizer import from_bytes

# nol di depan diikuti digit lain (mis. "081234567001", "007") bermakna — bukan angka biasa
_LEADING_ZERO_RE = re.compile(r"^0\d")


def _coerce_numeric_columns(df: pd.DataFrame) -> None:
    """Kolom yang seluruh isinya angka valid dikonversi ke tipe numerik, KECUALI ada nilai
    berawalan nol (kode pos, NIK, no HP) yang maknanya hilang jika dikonversi ke angka.
    Dibaca dengan dtype=str dulu supaya nol di depan tidak keburu hilang oleh auto-infer
    pandas sebelum sempat diperiksa di sini."""
    for col in df.columns:
        series = df[col]
        non_null = series.dropna()
        if non_null.empty:
            continue
        if non_null.map(lambda v: bool(_LEADING_ZERO_RE.match(str(v).strip()))).any():
            continue
        numeric = pd.to_numeric(non_null, errors="coerce")
        if numeric.notna().all():
            df[col] = pd.to_numeric(series, errors="coerce")


def load_dataframe(content: bytes, filename: str) -> pd.DataFrame:
    low = filename.lower()
    if low.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(content), dtype=str)
    else:
        best = from_bytes(content[:200_000]).best()
        encoding = best.encoding if best else "utf-8"
        text_sample = content[:100_000].decode(encoding, errors="replace")
        try:
            dialect = csv.Sniffer().sniff(text_sample, delimiters=",;\t|")
            sep = dialect.delimiter
        except csv.Error:
            sep = ","
        df = pd.read_csv(io.BytesIO(content), sep=sep, encoding=encoding,
                         encoding_errors="replace", low_memory=False, dtype=str)

    if df.empty:
        raise ValueError("File tidak berisi baris data")
    df.columns = [str(c).strip() for c in df.columns]
    empty_cols = [c for c in df.columns if df[c].isna().all()]
    if len(empty_cols) == len(df.columns):
        raise ValueError("Semua kolom kosong — file kemungkinan corrupt atau salah format")
    df = df.reset_index(drop=True)
    _coerce_numeric_columns(df)
    return df
