"""Clean dataset export — deliverable inti untuk konsumen hilir (data scientist dkk).

Menggabungkan standardisasi (services/standardization.py) dengan hasil entity resolution:
cluster yang sudah dikonfirmasi di-collapse menjadi satu baris golden record, sehingga
konsumen data tidak perlu mengulang kerja dedup & pembersihan sendiri. Baris yang belum
direview atau sudah direview sebagai entitas berbeda tetap tampil apa adanya, ditandai lewat
kolom `_dq_status` agar transparan (bukan disembunyikan diam-diam).
"""
from __future__ import annotations

import pandas as pd

from .standardization import standardize_dataframe

STATUS_UNIQUE = "unique"
STATUS_GOLDEN = "golden_record"
STATUS_PENDING = "pending_review"
STATUS_DISTINCT = "reviewed_distinct"


def build_clean_dataset(df: pd.DataFrame, clusters: list[dict]) -> tuple[pd.DataFrame, dict]:
    """clusters: [{status, cluster_key, members: [record_index,...], golden: dict|None}]."""
    std_df, _ = standardize_dataframe(df)
    std_df = std_df.copy()
    std_df["_dq_cluster_id"] = None
    std_df["_dq_status"] = STATUS_UNIQUE
    std_df["_dq_sort_key"] = std_df.index

    rows_to_drop: set[int] = set()
    golden_rows: list[dict] = []

    for cluster in clusters:
        members = [m for m in cluster["members"] if m in std_df.index]
        if not members:
            continue
        if cluster["status"] == "confirmed" and cluster.get("golden"):
            golden_row = dict(cluster["golden"])
            golden_row["_dq_cluster_id"] = cluster["cluster_key"]
            golden_row["_dq_status"] = STATUS_GOLDEN
            golden_row["_dq_source_rows"] = ",".join(f"r-{m}" for m in sorted(members))
            golden_row["_dq_sort_key"] = min(members)
            golden_rows.append(golden_row)
            rows_to_drop.update(members)
        else:
            status = STATUS_DISTINCT if cluster["status"] == "split" else STATUS_PENDING
            std_df.loc[members, "_dq_cluster_id"] = cluster["cluster_key"]
            std_df.loc[members, "_dq_status"] = status

    remaining = std_df.drop(index=[i for i in rows_to_drop if i in std_df.index])
    frames = [remaining]
    if golden_rows:
        frames.append(pd.DataFrame(golden_rows))
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values("_dq_sort_key").drop(columns=["_dq_sort_key"])
    combined = combined.reset_index(drop=True)

    summary = {
        "original_rows": len(df),
        "clean_rows": len(combined),
        "clusters_merged": len(golden_rows),
        "rows_collapsed": len(rows_to_drop),
        "pending_review_rows": int((std_df["_dq_status"] == STATUS_PENDING).sum()),
        "reviewed_distinct_rows": int((std_df["_dq_status"] == STATUS_DISTINCT).sum()),
    }
    return combined, summary
