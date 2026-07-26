from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    ActivityLog,
    ClusterMember,
    Dataset,
    EntityCluster,
    GoldenRecord,
    RecordMatchScore,
    User,
)
from ..security import get_current_user, require_writer
from ..services.golden_record import STRATEGY_LABELS, build_golden

router = APIRouter(tags=["clusters"])


class SurvivorshipBody(BaseModel):
    config: dict = {}


def _members_payload(db: Session, cluster_id: int) -> list[dict]:
    members = (db.query(ClusterMember).filter_by(cluster_id=cluster_id)
               .order_by(ClusterMember.record_index).all())
    return [{"record_index": m.record_index, "record_data": m.record_data} for m in members]


def _get_cluster(cluster_id: int, db: Session, user: User) -> tuple[EntityCluster, Dataset]:
    cluster = db.get(EntityCluster, cluster_id)
    if cluster is None:
        raise HTTPException(404, "Cluster tidak ditemukan")
    dataset = db.get(Dataset, cluster.dataset_id)
    if dataset is None or dataset.org_id != user.org_id:
        raise HTTPException(404, "Cluster tidak ditemukan")
    return cluster, dataset


def _cluster_dict(cluster: EntityCluster, dataset: Dataset | None = None,
                  with_members: bool = False, db: Session | None = None) -> dict:
    out = {
        "id": cluster.id,
        "dataset_id": cluster.dataset_id,
        "cluster_key": cluster.cluster_key,
        "cohesion": cluster.cohesion,
        "status": cluster.status,
        "record_count": cluster.record_count,
        "reviewed_by": cluster.reviewed_by,
        "reviewed_at": cluster.reviewed_at.isoformat() if cluster.reviewed_at else None,
    }
    if dataset is not None:
        out["dataset_name"] = dataset.name
    if with_members and db is not None:
        members = (db.query(ClusterMember).filter_by(cluster_id=cluster.id)
                   .order_by(ClusterMember.record_index).all())
        out["members"] = [{
            "id": m.id, "record_index": m.record_index, "record_data": m.record_data,
        } for m in members]
        # kolom yang nilainya berbeda antar anggota -> disorot di UI
        diff_columns = []
        if members:
            columns = set()
            for m in members:
                columns.update(m.record_data.keys())
            for col in columns:
                values = {str(m.record_data.get(col)) for m in members}
                if len(values) > 1:
                    diff_columns.append(col)
        out["diff_columns"] = diff_columns
        pairs = db.query(RecordMatchScore).filter_by(cluster_id=cluster.id).all()
        out["pairs"] = [{
            "record_a": p.record_a, "record_b": p.record_b,
            "score": p.score, "features": p.features,
        } for p in pairs]
    return out


@router.get("/review-queue")
def review_queue(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        db.query(EntityCluster, Dataset)
        .join(Dataset, EntityCluster.dataset_id == Dataset.id)
        .filter(Dataset.org_id == user.org_id, EntityCluster.status == "pending")
        .order_by(desc(EntityCluster.cohesion)).all()
    )
    return [_cluster_dict(cluster, dataset) for cluster, dataset in rows]


@router.get("/datasets/{dataset_id}/clusters")
def dataset_clusters(dataset_id: int, status: str | None = None, with_members: bool = False,
                     db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or dataset.org_id != user.org_id:
        raise HTTPException(404, "Dataset tidak ditemukan")
    query = db.query(EntityCluster).filter_by(dataset_id=dataset_id)
    if status:
        query = query.filter_by(status=status)
    return [_cluster_dict(c, dataset, with_members=with_members, db=db) for c in query.order_by(desc(EntityCluster.cohesion)).all()]


@router.get("/clusters/{cluster_id}")
def get_cluster(cluster_id: int, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    cluster, dataset = _get_cluster(cluster_id, db, user)
    return _cluster_dict(cluster, dataset, with_members=True, db=db)


@router.post("/clusters/{cluster_id}/confirm")
def confirm_cluster(cluster_id: int, db: Session = Depends(get_db),
                    user: User = Depends(require_writer)):
    cluster, dataset = _get_cluster(cluster_id, db, user)
    if cluster.status != "pending":
        raise HTTPException(409, "Cluster sudah direview")
    members = db.query(ClusterMember).filter_by(cluster_id=cluster.id).all()
    if len(members) < 2:
        raise HTTPException(409, "Cluster butuh minimal 2 record untuk dikonfirmasi")

    golden_data, provenance = build_golden(
        [{"record_index": m.record_index, "record_data": m.record_data} for m in members],
        dataset.survivorship_config,
    )
    golden = GoldenRecord(dataset_id=dataset.id, cluster_id=cluster.id,
                          data=golden_data, provenance=provenance, created_by=user.email)
    db.add(golden)

    cluster.status = "confirmed"
    cluster.reviewed_by = user.email
    cluster.reviewed_at = datetime.utcnow()
    db.add(ActivityLog(org_id=user.org_id,
                       message=f'Cluster {cluster.cluster_key} ({dataset.name}) dikonfirmasi '
                               f"oleh {user.email}, golden record dibuat"))
    db.commit()
    return {"status": "confirmed", "golden_record_id": golden.id}


@router.post("/clusters/{cluster_id}/split")
def split_cluster(cluster_id: int, db: Session = Depends(get_db),
                  user: User = Depends(require_writer)):
    cluster, dataset = _get_cluster(cluster_id, db, user)
    if cluster.status != "pending":
        raise HTTPException(409, "Cluster sudah direview")
    cluster.status = "split"
    cluster.reviewed_by = user.email
    cluster.reviewed_at = datetime.utcnow()
    db.add(ActivityLog(org_id=user.org_id,
                       message=f'Cluster {cluster.cluster_key} ({dataset.name}) di-split '
                               f"(bukan entitas sama) oleh {user.email}"))
    db.commit()
    return {"status": "split"}


class ExcludeMember(BaseModel):
    member_id: int


@router.post("/clusters/{cluster_id}/exclude-member")
def exclude_member(cluster_id: int, body: ExcludeMember, db: Session = Depends(get_db),
                   user: User = Depends(require_writer)):
    cluster, dataset = _get_cluster(cluster_id, db, user)
    if cluster.status != "pending":
        raise HTTPException(409, "Cluster sudah direview")
    member = db.get(ClusterMember, body.member_id)
    if member is None or member.cluster_id != cluster.id:
        raise HTTPException(404, "Anggota cluster tidak ditemukan")
    db.delete(member)
    db.flush()

    remaining = db.query(ClusterMember).filter_by(cluster_id=cluster.id).all()
    cluster.record_count = len(remaining)
    if len(remaining) < 2:
        cluster.status = "split"
        cluster.reviewed_by = user.email
        cluster.reviewed_at = datetime.utcnow()
    else:
        # hitung ulang cohesion dari pasangan yang tersisa
        indices = {m.record_index for m in remaining}
        pairs = db.query(RecordMatchScore).filter_by(cluster_id=cluster.id).all()
        remaining_scores = [p.score for p in pairs
                            if p.record_a in indices and p.record_b in indices]
        if remaining_scores:
            cluster.cohesion = round(sum(remaining_scores) / len(remaining_scores), 4)
    db.add(ActivityLog(org_id=user.org_id,
                       message=f"Record r-{member.record_index} dikeluarkan dari cluster "
                               f"{cluster.cluster_key} ({dataset.name}) oleh {user.email}"))
    db.commit()
    return {"status": cluster.status, "record_count": cluster.record_count}


class MergeClusters(BaseModel):
    other_cluster_id: int


@router.post("/clusters/{cluster_id}/merge")
def merge_clusters(cluster_id: int, body: MergeClusters, db: Session = Depends(get_db),
                   user: User = Depends(require_writer)):
    cluster, dataset = _get_cluster(cluster_id, db, user)
    other, other_ds = _get_cluster(body.other_cluster_id, db, user)
    if other_ds.id != dataset.id:
        raise HTTPException(400, "Cluster harus berasal dari dataset yang sama")
    if cluster.status != "pending" or other.status != "pending":
        raise HTTPException(409, "Kedua cluster harus berstatus pending")

    for member in db.query(ClusterMember).filter_by(cluster_id=other.id).all():
        member.cluster_id = cluster.id
    for pair in db.query(RecordMatchScore).filter_by(cluster_id=other.id).all():
        pair.cluster_id = cluster.id
    db.delete(other)
    db.flush()
    cluster.record_count = db.query(ClusterMember).filter_by(cluster_id=cluster.id).count()
    db.add(ActivityLog(org_id=user.org_id,
                       message=f"Cluster {other.cluster_key} digabung ke {cluster.cluster_key} "
                               f"({dataset.name}) oleh {user.email}"))
    db.commit()
    return {"status": "merged", "record_count": cluster.record_count}


@router.get("/survivorship-strategies")
def survivorship_strategies():
    return [{"key": k, "label": v} for k, v in STRATEGY_LABELS.items()]


@router.get("/clusters/{cluster_id}/golden")
def get_golden(cluster_id: int, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    cluster, dataset = _get_cluster(cluster_id, db, user)
    golden = db.query(GoldenRecord).filter_by(cluster_id=cluster.id).first()
    if golden is None:
        raise HTTPException(404, "Golden record belum dibuat untuk cluster ini")
    return {
        "cluster": _cluster_dict(cluster, dataset),
        "members": _members_payload(db, cluster.id),
        "golden": golden.data,
        "provenance": golden.provenance,
        "created_by": golden.created_by,
        "created_at": golden.created_at.isoformat(),
        "config": dataset.survivorship_config or {},
        "strategies": [{"key": k, "label": v} for k, v in STRATEGY_LABELS.items()],
    }


@router.post("/clusters/{cluster_id}/golden/preview")
def preview_golden(cluster_id: int, body: SurvivorshipBody, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    """Hitung golden record dengan konfigurasi survivorship tertentu tanpa menyimpan."""
    cluster, _ = _get_cluster(cluster_id, db, user)
    members = _members_payload(db, cluster.id)
    if len(members) < 2:
        raise HTTPException(409, "Cluster butuh minimal 2 record")
    golden_data, provenance = build_golden(members, body.config)
    return {"golden": golden_data, "provenance": provenance}


@router.put("/clusters/{cluster_id}/golden")
def rebuild_golden(cluster_id: int, body: SurvivorshipBody, db: Session = Depends(get_db),
                   user: User = Depends(require_writer)):
    """Bangun ulang golden record dengan konfigurasi baru; konfigurasi tersimpan
    sebagai default survivorship dataset untuk konfirmasi cluster berikutnya."""
    cluster, dataset = _get_cluster(cluster_id, db, user)
    golden = db.query(GoldenRecord).filter_by(cluster_id=cluster.id).first()
    if golden is None:
        raise HTTPException(404, "Golden record belum dibuat untuk cluster ini")

    members = _members_payload(db, cluster.id)
    golden_data, provenance = build_golden(members, body.config)
    golden.data = golden_data
    golden.provenance = provenance
    golden.created_by = user.email
    dataset.survivorship_config = body.config
    db.add(ActivityLog(org_id=user.org_id,
                       message=f"Golden record {cluster.cluster_key} ({dataset.name}) "
                               f"dibangun ulang dengan aturan survivorship baru "
                               f"oleh {user.email}"))
    db.commit()
    return {"golden": golden_data, "provenance": provenance}
