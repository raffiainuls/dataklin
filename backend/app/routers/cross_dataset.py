import traceback
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Alert, CrossDatasetRule, Dataset, DatasetColumn, Organization, User
from ..security import get_current_user, require_writer
from ..services import storage
from ..services.cross_dataset_checks import check_consistency, check_referential_integrity
from ..services.loader import load_dataframe
from ..services.notifier import notify_alert

router = APIRouter(tags=["cross-dataset"])

CHECK_TYPES = {
    "referential_integrity": "Referential Integrity (FK harus ada di dataset lain)",
    "consistency": "Consistency (nilai harus sama antar dataset untuk kunci yang sama)",
}


class CrossDatasetRuleCreate(BaseModel):
    name: str
    check_type: str = "referential_integrity"
    primary_dataset_id: int
    primary_column: str
    reference_dataset_id: int
    reference_column: str
    primary_value_column: str | None = None
    reference_value_column: str | None = None


def _dict(r: CrossDatasetRule, dataset_names: dict[int, str]) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "check_type": r.check_type,
        "check_type_label": CHECK_TYPES.get(r.check_type, r.check_type),
        "primary_dataset_id": r.primary_dataset_id,
        "primary_dataset_name": dataset_names.get(r.primary_dataset_id, "-"),
        "primary_column": r.primary_column,
        "primary_value_column": r.primary_value_column,
        "reference_dataset_id": r.reference_dataset_id,
        "reference_dataset_name": dataset_names.get(r.reference_dataset_id, "-"),
        "reference_column": r.reference_column,
        "reference_value_column": r.reference_value_column,
        "enabled": r.enabled,
        "created_by": r.created_by,
        "created_at": r.created_at.isoformat(),
        "last_checked_at": r.last_checked_at.isoformat() if r.last_checked_at else None,
        "last_checked_count": r.last_checked_count,
        "last_violations": r.last_violations,
        "last_samples": r.last_samples,
    }


def _get_ready_dataset(dataset_id: int, db: Session, user: User) -> Dataset:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or dataset.org_id != user.org_id:
        raise HTTPException(404, f"Dataset {dataset_id} tidak ditemukan")
    if dataset.status != "ready":
        raise HTTPException(409, f'Dataset "{dataset.name}" belum selesai diproses')
    return dataset


def _column_exists(db: Session, dataset_id: int, column: str) -> bool:
    return db.query(DatasetColumn).filter_by(dataset_id=dataset_id, name=column).first() is not None


@router.get("/cross-dataset-check-types")
def cross_dataset_check_types():
    return [{"type": k, "label": v} for k, v in CHECK_TYPES.items()]


@router.get("/cross-dataset-rules")
def list_cross_dataset_rules(db: Session = Depends(get_db),
                             user: User = Depends(get_current_user)):
    rules = db.query(CrossDatasetRule).filter_by(org_id=user.org_id).order_by(
        CrossDatasetRule.created_at.desc()).all()
    dataset_ids = {r.primary_dataset_id for r in rules} | {r.reference_dataset_id for r in rules}
    dataset_names = {}
    if dataset_ids:
        dataset_names = {d.id: d.name for d in
                         db.query(Dataset).filter(Dataset.id.in_(dataset_ids)).all()}
    return [_dict(r, dataset_names) for r in rules]


@router.post("/cross-dataset-rules")
def create_cross_dataset_rule(body: CrossDatasetRuleCreate, db: Session = Depends(get_db),
                              user: User = Depends(require_writer)):
    if body.check_type not in CHECK_TYPES:
        raise HTTPException(400, f"check_type harus salah satu dari: {', '.join(CHECK_TYPES)}")
    primary = _get_ready_dataset(body.primary_dataset_id, db, user)
    reference = _get_ready_dataset(body.reference_dataset_id, db, user)
    if not _column_exists(db, primary.id, body.primary_column):
        raise HTTPException(400, f'Kolom "{body.primary_column}" tidak ada di "{primary.name}"')
    if not _column_exists(db, reference.id, body.reference_column):
        raise HTTPException(400,
                            f'Kolom "{body.reference_column}" tidak ada di "{reference.name}"')

    if body.check_type == "consistency":
        if not body.primary_value_column or not body.reference_value_column:
            raise HTTPException(400,
                                "Consistency check butuh primary_value_column & "
                                "reference_value_column (kolom yang dibandingkan)")
        if not _column_exists(db, primary.id, body.primary_value_column):
            raise HTTPException(400,
                                f'Kolom "{body.primary_value_column}" tidak ada di "{primary.name}"')
        if not _column_exists(db, reference.id, body.reference_value_column):
            raise HTTPException(400,
                                f'Kolom "{body.reference_value_column}" tidak ada di '
                                f'"{reference.name}"')

    rule = CrossDatasetRule(
        org_id=user.org_id, name=body.name.strip() or f"{primary.name} → {reference.name}",
        check_type=body.check_type,
        primary_dataset_id=primary.id, primary_column=body.primary_column,
        reference_dataset_id=reference.id, reference_column=body.reference_column,
        primary_value_column=body.primary_value_column if body.check_type == "consistency" else None,
        reference_value_column=(body.reference_value_column
                                if body.check_type == "consistency" else None),
        created_by=user.email,
    )
    db.add(rule)
    db.commit()
    return _dict(rule, {primary.id: primary.name, reference.id: reference.name})


@router.delete("/cross-dataset-rules/{rule_id}")
def delete_cross_dataset_rule(rule_id: int, db: Session = Depends(get_db),
                              user: User = Depends(require_writer)):
    rule = db.get(CrossDatasetRule, rule_id)
    if rule is None or rule.org_id != user.org_id:
        raise HTTPException(404, "Rule tidak ditemukan")
    db.delete(rule)
    db.commit()
    return {"deleted": True}


@router.post("/cross-dataset-rules/{rule_id}/run")
def run_cross_dataset_rule(rule_id: int, db: Session = Depends(get_db),
                          user: User = Depends(require_writer)):
    rule = db.get(CrossDatasetRule, rule_id)
    if rule is None or rule.org_id != user.org_id:
        raise HTTPException(404, "Rule tidak ditemukan")
    primary = _get_ready_dataset(rule.primary_dataset_id, db, user)
    reference = _get_ready_dataset(rule.reference_dataset_id, db, user)

    primary_content = storage.get_object(primary.storage_key)
    primary_df = load_dataframe(primary_content, primary.filename)
    reference_content = storage.get_object(reference.storage_key)
    reference_df = load_dataframe(reference_content, reference.filename)

    try:
        if rule.check_type == "consistency":
            result = check_consistency(
                primary_df, rule.primary_column, rule.primary_value_column,
                reference_df, rule.reference_column, rule.reference_value_column,
            )
            subject = (f'"{primary.name}.{rule.primary_value_column}" vs '
                      f'"{reference.name}.{rule.reference_value_column}" '
                      f'(join {rule.primary_column}={rule.reference_column})')
        else:
            result = check_referential_integrity(primary_df, rule.primary_column,
                                                 reference_df, rule.reference_column)
            subject = (f'"{primary.name}.{rule.primary_column}" tidak ditemukan di '
                      f'"{reference.name}.{rule.reference_column}"')
    except ValueError as exc:
        raise HTTPException(409, str(exc))

    rule.last_checked_at = datetime.utcnow()
    rule.last_checked_count = result["checked"]
    rule.last_violations = result["violations"]
    rule.last_samples = result["samples"]

    if result["violations"] > 0:
        ratio = result["violations"] / result["checked"] if result["checked"] else 0
        severity = "tinggi" if ratio > 0.1 else "sedang"
        alert_type = ("konsistensi_lintas_sistem" if rule.check_type == "consistency"
                      else "integritas_referensial")
        alert = Alert(
            org_id=user.org_id, dataset_id=primary.id, alert_type=alert_type, severity=severity,
            message=f'{CHECK_TYPES[rule.check_type]} "{rule.name}": {result["violations"]} '
                    f'dari {result["checked"]} {subject}',
        )
        db.add(alert)
        org = db.get(Organization, user.org_id)
        if org is not None:
            try:
                notify_alert(org, alert)
            except Exception:  # noqa: BLE001 - notifikasi gagal tidak boleh gagalkan hasil cek
                traceback.print_exc()

    db.commit()
    return _dict(rule, {primary.id: primary.name, reference.id: reference.name})
