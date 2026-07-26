"""Cek lintas-dataset, dijalankan on-demand terhadap dua DataFrame yang sudah dimuat:

- Referential Integrity Check (backlog #10): nilai kolom anak (FK) yang tidak ditemukan
  di kolom induk (PK) dataset lain.
- Consistency Check antar sistem/tabel (backlog #11): join dua dataset lewat kolom kunci,
  bandingkan kolom nilai untuk baris yang cocok — deteksi nilai yang seharusnya sama tapi
  berbeda antar sumber (mis. status pelanggan berbeda antara CRM & billing).
"""
from __future__ import annotations

import pandas as pd

MAX_SAMPLES = 10


def _stringify(series: pd.Series) -> pd.Series:
    """Representasi teks yang aman untuk kolom ID numerik — hindari 'NIK...001.0'
    (lihat memori dataklin-numeric-id-display-bug: pola berulang di codebase ini)."""
    non_null = series.dropna()
    if pd.api.types.is_float_dtype(series) and len(non_null) and (non_null % 1 == 0).all():
        series = series.astype("Int64")
    return series.astype(str)


def check_referential_integrity(primary_df: pd.DataFrame, primary_column: str,
                                reference_df: pd.DataFrame, reference_column: str) -> dict:
    """Kembalikan {checked, violations, samples} — checked = jumlah nilai non-kosong di
    primary_column, violations = berapa di antaranya tidak ditemukan di reference_column."""
    if primary_column not in primary_df.columns:
        raise ValueError(f'Kolom "{primary_column}" tidak ditemukan di dataset utama')
    if reference_column not in reference_df.columns:
        raise ValueError(f'Kolom "{reference_column}" tidak ditemukan di dataset referensi')

    primary_values = _stringify(primary_df[primary_column].dropna())
    reference_set = set(_stringify(reference_df[reference_column].dropna()))

    checked = len(primary_values)
    missing_mask = ~primary_values.isin(reference_set)
    violations = int(missing_mask.sum())
    samples = primary_values[missing_mask].drop_duplicates().head(MAX_SAMPLES).tolist()
    return {"checked": checked, "violations": violations, "samples": samples}


def _norm_value(value: str) -> str | None:
    if value in (None, "nan", "None", "<NA>"):
        return None
    return value.strip().lower()


def check_consistency(primary_df: pd.DataFrame, primary_key_column: str,
                      primary_value_column: str, reference_df: pd.DataFrame,
                      reference_key_column: str, reference_value_column: str) -> dict:
    """Kembalikan {checked, violations, samples} — checked = jumlah baris yang berhasil
    di-join lewat kunci (ada di kedua sisi, keduanya non-kosong), violations = di antaranya
    yang nilai kolom pembandingnya berbeda (dibandingkan case-insensitive, whitespace
    dirapikan — perbedaan format murni tidak dianggap inkonsistensi data)."""
    for column, df, side in (
        (primary_key_column, primary_df, "utama"),
        (primary_value_column, primary_df, "utama"),
        (reference_key_column, reference_df, "referensi"),
        (reference_value_column, reference_df, "referensi"),
    ):
        if column not in df.columns:
            raise ValueError(f'Kolom "{column}" tidak ditemukan di dataset {side}')

    primary_subset = primary_df[[primary_key_column, primary_value_column]].dropna()
    left = pd.DataFrame({
        "_key": _stringify(primary_subset[primary_key_column]),
        "_primary_value": _stringify(primary_subset[primary_value_column]),
    })
    reference_subset = reference_df[[reference_key_column, reference_value_column]].dropna()
    right = pd.DataFrame({
        "_key": _stringify(reference_subset[reference_key_column]),
        "_reference_value": _stringify(reference_subset[reference_value_column]),
    })

    merged = left.merge(right, on="_key", how="inner")
    checked = len(merged)
    mismatch = (merged["_primary_value"].map(_norm_value)
                != merged["_reference_value"].map(_norm_value))
    violations = int(mismatch.sum())
    sample_rows = merged[mismatch].head(MAX_SAMPLES)
    samples = [
        f'{row["_key"]}: "{row["_primary_value"]}" vs "{row["_reference_value"]}"'
        for _, row in sample_rows.iterrows()
    ]
    return {"checked": checked, "violations": violations, "samples": samples}
