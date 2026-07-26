import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import (
    ActivityLog,
    Alert,
    Anomaly,
    ClusterMember,
    DataConnection,
    Dataset,
    DatasetColumn,
    EntityCluster,
    GoldenRecord,
    RuleResult,
    User,
    ValidationRule,
)
from ..security import Actor, get_current_user, get_org_reader, require_writer
from ..services import storage
from ..services.rule_engine import RULE_TYPES
from ..worker.queue import enqueue_process_dataset, enqueue_refresh_dataset

router = APIRouter(tags=["datasets"])


def _dataset_dict(ds: Dataset, pending_clusters: int | None = None) -> dict:
    out = {
        "id": ds.id,
        "name": ds.name,
        "filename": ds.filename,
        "status": ds.status,
        "error_message": ds.error_message,
        "row_count": ds.row_count,
        "column_count": ds.column_count,
        "quality_score": ds.quality_score,
        "dimensions": ds.dimensions,
        "source_type": ds.source_type,
        "connection_id": ds.connection_id,
        "monitoring_enabled": ds.monitoring_enabled,
        "monitoring_interval_minutes": ds.monitoring_interval_minutes,
        "created_at": ds.created_at.isoformat(),
        "updated_at": ds.updated_at.isoformat(),
    }
    if pending_clusters is not None:
        out["pending_clusters"] = pending_clusters
    return out


@router.post("/datasets/upload")
async def upload_dataset(file: UploadFile, db: Session = Depends(get_db),
                         user: User = Depends(require_writer)):
    filename = file.filename or "dataset.csv"
    if not filename.lower().endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(400, "Format file harus CSV atau XLSX")
    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(400, f"Ukuran file melebihi {settings.max_upload_mb}MB")
    if not content:
        raise HTTPException(400, "File kosong")

    key = f"datasets/{uuid.uuid4().hex}/{filename}"
    storage.put_object(key, content)

    dataset = Dataset(org_id=user.org_id, name=filename, filename=filename,
                      storage_key=key, status="queued")
    db.add(dataset)
    db.add(ActivityLog(org_id=user.org_id,
                       message=f'Dataset "{filename}" diunggah oleh {user.name}'))
    db.commit()
    enqueue_process_dataset(dataset.id)
    return _dataset_dict(dataset)


class DatasetFromConnection(BaseModel):
    connection_id: int
    name: str
    query: str


@router.post("/datasets/from-connection")
def create_from_connection(body: DatasetFromConnection, db: Session = Depends(get_db),
                           user: User = Depends(require_writer)):
    """Dataset dari koneksi database langsung (backlog #2) alih-alih upload file."""
    connection = db.get(DataConnection, body.connection_id)
    if connection is None or connection.org_id != user.org_id:
        raise HTTPException(404, "Koneksi tidak ditemukan")
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Nama dataset tidak boleh kosong")
    if not body.query.strip():
        raise HTTPException(400, "Query tidak boleh kosong")

    filename = f"{name}.csv"
    key = f"datasets/{uuid.uuid4().hex}/{filename}"
    dataset = Dataset(org_id=user.org_id, name=name, filename=filename, storage_key=key,
                      status="queued", source_type="database",
                      connection_id=connection.id, source_query=body.query.strip())
    db.add(dataset)
    db.add(ActivityLog(org_id=user.org_id,
                       message=f'Dataset "{name}" dibuat dari koneksi "{connection.name}" '
                               f"oleh {user.name}"))
    db.commit()
    enqueue_refresh_dataset(dataset.id)
    return _dataset_dict(dataset)


@router.get("/datasets")
def list_datasets(db: Session = Depends(get_db), user: Actor = Depends(get_org_reader)):
    datasets = (
        db.query(Dataset).filter_by(org_id=user.org_id)
        .order_by(desc(Dataset.updated_at)).all()
    )
    pending = dict(
        db.query(EntityCluster.dataset_id, func.count(EntityCluster.id))
        .filter(EntityCluster.status == "pending")
        .group_by(EntityCluster.dataset_id).all()
    )
    return [_dataset_dict(ds, pending.get(ds.id, 0)) for ds in datasets]


@router.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: int, db: Session = Depends(get_db),
                user: Actor = Depends(get_org_reader)):
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or dataset.org_id != user.org_id:
        raise HTTPException(404, "Dataset tidak ditemukan")

    columns = (
        db.query(DatasetColumn).filter_by(dataset_id=dataset.id)
        .order_by(DatasetColumn.position).all()
    )
    pending_clusters = db.query(EntityCluster).filter_by(
        dataset_id=dataset.id, status="pending").count()
    total_clusters = db.query(EntityCluster).filter_by(dataset_id=dataset.id).count()

    rule_summary = (
        db.query(func.count(RuleResult.id), func.coalesce(func.sum(RuleResult.violations), 0))
        .filter(RuleResult.dataset_id == dataset.id).first()
    )

    out = _dataset_dict(dataset, pending_clusters)
    out["total_clusters"] = total_clusters
    out["rule_runs"] = rule_summary[0]
    out["rule_violations"] = int(rule_summary[1])
    out["columns"] = [{
        "id": c.id,
        "name": c.name,
        "inferred_type": c.inferred_type,
        "completeness": c.completeness,
        "uniqueness": c.uniqueness,
        "validity": c.validity,
        "consistency": c.consistency,
        "null_count": c.null_count,
        "unique_count": c.unique_count,
        "top_values": c.top_values,
        "stats": c.stats,
        "notes": c.notes,
    } for c in columns]
    return out


def _load_ready_dataset_df(dataset_id: int, db: Session, user: Actor):
    from ..services.loader import load_dataframe

    dataset = db.get(Dataset, dataset_id)
    if dataset is None or dataset.org_id != user.org_id:
        raise HTTPException(404, "Dataset tidak ditemukan")
    if dataset.status != "ready":
        raise HTTPException(409, "Dataset belum selesai diproses")
    content = storage.get_object(dataset.storage_key)
    return dataset, load_dataframe(content, dataset.filename)


@router.post("/datasets/{dataset_id}/standardize/preview")
def standardize_preview(dataset_id: int, db: Session = Depends(get_db),
                        user: Actor = Depends(get_org_reader)):
    from ..services.standardization import standardize_dataframe

    _, df = _load_ready_dataset_df(dataset_id, db, user)
    _, report = standardize_dataframe(df)
    return {
        "total_changes": sum(r["changed"] for r in report),
        "total_rows": len(df),
        "columns": report,
    }


@router.get("/datasets/{dataset_id}/standardized.csv")
def standardized_csv(dataset_id: int, db: Session = Depends(get_db),
                     user: Actor = Depends(get_org_reader)):
    from ..services.standardization import standardize_dataframe

    dataset, df = _load_ready_dataset_df(dataset_id, db, user)
    std_df, _ = standardize_dataframe(df)
    buf = io.StringIO()
    std_df.to_csv(buf, index=False)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition":
                 f'attachment; filename="standardized_{dataset.id}.csv"'},
    )


@router.post("/datasets/{dataset_id}/standardize/apply")
def standardize_apply(dataset_id: int, db: Session = Depends(get_db),
                      user: User = Depends(require_writer)):
    """Simpan hasil standardisasi sebagai dataset baru dan proses ulang penuh
    (profiling, rules, entity resolution) lewat pipeline yang sama."""
    from ..services.standardization import standardize_dataframe

    dataset, df = _load_ready_dataset_df(dataset_id, db, user)
    std_df, report = standardize_dataframe(df)

    stem = dataset.filename.rsplit(".", 1)[0]
    new_filename = f"{stem}_standardized.csv"
    buf = io.StringIO()
    std_df.to_csv(buf, index=False)
    key = f"datasets/{uuid.uuid4().hex}/{new_filename}"
    storage.put_object(key, buf.getvalue().encode("utf-8"))

    new_dataset = Dataset(org_id=user.org_id, name=new_filename, filename=new_filename,
                          storage_key=key, status="queued")
    db.add(new_dataset)
    total_changes = sum(r["changed"] for r in report)
    db.add(ActivityLog(org_id=user.org_id,
                       message=f'Dataset "{new_filename}" dibuat dari standardisasi '
                               f'"{dataset.name}" ({total_changes} nilai dinormalisasi) '
                               f"oleh {user.name}"))
    db.commit()
    enqueue_process_dataset(new_dataset.id)
    return {"dataset_id": new_dataset.id, "name": new_filename,
            "total_changes": total_changes}


def _fetch_cluster_payload(dataset_id: int, db: Session) -> list[dict]:
    clusters = db.query(EntityCluster).filter_by(dataset_id=dataset_id).all()
    payload = []
    for cluster in clusters:
        members = db.query(ClusterMember).filter_by(cluster_id=cluster.id).all()
        golden = None
        if cluster.status == "confirmed":
            record = db.query(GoldenRecord).filter_by(cluster_id=cluster.id).first()
            golden = record.data if record else None
        payload.append({
            "status": cluster.status,
            "cluster_key": cluster.cluster_key,
            "members": [m.record_index for m in members],
            "golden": golden,
        })
    return payload


@router.get("/datasets/{dataset_id}/clean/preview")
def clean_preview(dataset_id: int, db: Session = Depends(get_db),
                  user: Actor = Depends(get_org_reader)):
    from ..services.clean_export import build_clean_dataset

    dataset, df = _load_ready_dataset_df(dataset_id, db, user)
    _, summary = build_clean_dataset(df, _fetch_cluster_payload(dataset.id, db))
    return summary


@router.get("/datasets/{dataset_id}/pii")
def list_pii(dataset_id: int, db: Session = Depends(get_db),
            user: Actor = Depends(get_org_reader)):
    """Kolom PII terdeteksi otomatis + rekomendasi masking (F11)."""
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or dataset.org_id != user.org_id:
        raise HTTPException(404, "Dataset tidak ditemukan")
    return dataset.pii_findings or []


@router.get("/datasets/{dataset_id}/clean.csv")
def clean_csv(dataset_id: int, mask_pii: bool = False, db: Session = Depends(get_db),
             user: Actor = Depends(get_org_reader)):
    """Dataset siap-konsumsi: standardisasi + duplikat dikonfirmasi digabung ke golden
    record dalam satu baris. Kolom `_dq_*` menandai asal & status tiap baris (transparan,
    tidak menyembunyikan apa pun) — untuk konsumen yang butuh data mentah tanpa penanda,
    tinggal drop kolom berprefiks `_dq_`. Set `mask_pii=true` untuk menyamarkan kolom
    sensitif (NIK, HP, email, nama, alamat) sebelum data dibagikan ke konsumen hilir."""
    from ..services.clean_export import build_clean_dataset

    dataset, df = _load_ready_dataset_df(dataset_id, db, user)
    clean_df, _ = build_clean_dataset(df, _fetch_cluster_payload(dataset.id, db))
    if mask_pii and dataset.pii_findings:
        from ..services.pii import mask_dataframe
        clean_df = mask_dataframe(clean_df, dataset.pii_findings)
    buf = io.StringIO()
    clean_df.to_csv(buf, index=False)
    suffix = "_masked" if mask_pii else ""
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition":
                 f'attachment; filename="clean_{dataset.id}{suffix}.csv"'},
    )


@router.get("/datasets/{dataset_id}/dictionary.csv")
def dictionary_csv(dataset_id: int, db: Session = Depends(get_db),
                   user: Actor = Depends(get_org_reader)):
    """Data dictionary: skema & statistik profiling per kolom + rule aktif yang berlaku,
    supaya konsumen hilir tidak perlu re-derive statistik sendiri."""
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or dataset.org_id != user.org_id:
        raise HTTPException(404, "Dataset tidak ditemukan")
    if dataset.status != "ready":
        raise HTTPException(409, "Dataset belum selesai diproses")

    columns = (db.query(DatasetColumn).filter_by(dataset_id=dataset_id)
               .order_by(DatasetColumn.position).all())
    rules = db.query(ValidationRule).filter_by(dataset_id=dataset_id, enabled=True).all()
    rules_by_column: dict[str, list[str]] = {}
    for rule in rules:
        label = rule.description or RULE_TYPES.get(rule.rule_type, rule.rule_type)
        rules_by_column.setdefault(rule.column_name, []).append(label)
    pii_by_column = {f["column_name"]: f for f in (dataset.pii_findings or [])}

    import csv as csv_module

    buf = io.StringIO()
    writer = csv_module.writer(buf)
    writer.writerow(["dataset", dataset.name, "baris", dataset.row_count,
                     "skor_kualitas", dataset.quality_score])
    writer.writerow([])
    writer.writerow(["kolom", "tipe", "completeness", "uniqueness", "validity",
                     "consistency", "null_count", "unique_count", "nilai_teratas",
                     "catatan", "rule_aktif", "pii"])
    for col in columns:
        pii = pii_by_column.get(col.name)
        if pii:
            # dictionary bukan endpoint pengambilan data — nilai asli tidak ditampilkan
            # untuk kolom PII, cukup contoh yang sudah disamarkan
            top_values = f'[PII: {pii["pii_label"]}] contoh: {pii["sample_masked"]}'
        else:
            top_values = "; ".join(
                f'{t["value"]} ({t["count"]})' for t in (col.top_values or [])[:5])
        rule_desc = "; ".join(rules_by_column.get(col.name, []))
        writer.writerow([col.name, col.inferred_type, col.completeness, col.uniqueness,
                         col.validity, col.consistency, col.null_count, col.unique_count,
                         top_values, col.notes, rule_desc,
                         pii["pii_label"] if pii else ""])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition":
                 f'attachment; filename="dictionary_{dataset.id}.csv"'},
    )


@router.get("/datasets/{dataset_id}/anomalies")
def list_anomalies(dataset_id: int, db: Session = Depends(get_db),
                   user: Actor = Depends(get_org_reader)):
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or dataset.org_id != user.org_id:
        raise HTTPException(404, "Dataset tidak ditemukan")
    anomalies = (
        db.query(Anomaly).filter_by(dataset_id=dataset_id)
        .order_by(Anomaly.column_name, Anomaly.record_index).all()
    )
    return [{
        "id": a.id,
        "column_name": a.column_name,
        "record_index": a.record_index,
        "anomaly_type": a.anomaly_type,
        "value": a.value,
        "explanation": a.explanation,
        "severity": a.severity,
    } for a in anomalies]


@router.get("/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    datasets = db.query(Dataset).filter_by(org_id=user.org_id).all()
    scores = [d.quality_score for d in datasets if d.quality_score is not None]
    dataset_ids = [d.id for d in datasets]

    total_clusters = 0
    if dataset_ids:
        total_clusters = db.query(EntityCluster).filter(
            EntityCluster.dataset_id.in_(dataset_ids)).count()
    active_alerts = db.query(Alert).filter_by(org_id=user.org_id, status="open").count()

    recent = sorted(datasets, key=lambda d: d.updated_at, reverse=True)[:5]
    pending = {}
    if dataset_ids:
        pending = dict(
            db.query(EntityCluster.dataset_id, func.count(EntityCluster.id))
            .filter(EntityCluster.status == "pending",
                    EntityCluster.dataset_id.in_(dataset_ids))
            .group_by(EntityCluster.dataset_id).all()
        )
    activities = (
        db.query(ActivityLog).filter_by(org_id=user.org_id)
        .order_by(desc(ActivityLog.created_at)).limit(8).all()
    )
    return {
        "total_datasets": len(datasets),
        "avg_quality_score": round(sum(scores) / len(scores), 1) if scores else None,
        "duplicate_clusters": total_clusters,
        "active_alerts": active_alerts,
        "recent_datasets": [_dataset_dict(d, pending.get(d.id, 0)) for d in recent],
        "recent_activity": [
            {"message": a.message, "created_at": a.created_at.isoformat()} for a in activities
        ],
    }
