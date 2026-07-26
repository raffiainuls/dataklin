from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Dataset, DatasetColumn, RuleResult, User, ValidationRule
from ..security import get_current_user, require_writer
from ..services.llm import LLMNotConfigured, generate_rule, llm_available, suggest_rules
from ..services.rule_engine import RULE_TYPES
from ..worker.queue import enqueue_refresh_dataset

router = APIRouter(tags=["rules"])


class RuleCreate(BaseModel):
    column_name: str
    rule_type: str
    params: dict | None = None
    description: str = ""
    source: str = "manual"  # manual | ai


class RuleGenerate(BaseModel):
    instruction: str


class RuleUpdate(BaseModel):
    enabled: bool


def _get_dataset(dataset_id: int, db: Session, user: User) -> Dataset:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or dataset.org_id != user.org_id:
        raise HTTPException(404, "Dataset tidak ditemukan")
    return dataset


def _column_info(db: Session, dataset_id: int) -> list[DatasetColumn]:
    columns = (db.query(DatasetColumn).filter_by(dataset_id=dataset_id)
               .order_by(DatasetColumn.position).all())
    if not columns:
        raise HTTPException(409, "Dataset belum selesai diprofilkan")
    return columns


def _validate_proposal(proposal: dict, valid_columns: set[str]) -> dict:
    """Validasi proposal rule dari LLM: rule_type dikenal & kolom benar-benar ada di
    dataset. Sama dipakai untuk NL generation (satu proposal) & auto-suggest (banyak)."""
    rule_type = proposal.get("rule_type")
    if rule_type not in RULE_TYPES:
        raise HTTPException(502, f"LLM mengembalikan rule_type tidak dikenal: {rule_type}")
    params = proposal.get("params") or {}
    if rule_type == "cross_column":
        if params.get("left") not in valid_columns or params.get("right") not in valid_columns:
            raise HTTPException(502, "LLM merujuk kolom yang tidak ada di dataset")
        column_name = params.get("left")
    else:
        column_name = proposal.get("column_name")
        if column_name not in valid_columns:
            raise HTTPException(502, f"LLM merujuk kolom tidak dikenal: {column_name}")
    return {
        "column_name": column_name,
        "rule_type": rule_type,
        "params": params,
        "description": proposal.get("description", ""),
        "rule_label": RULE_TYPES[rule_type],
    }


@router.get("/rule-types")
def rule_types():
    return [{"type": k, "label": v} for k, v in RULE_TYPES.items()]


@router.get("/datasets/{dataset_id}/rules")
def list_rules(dataset_id: int, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    _get_dataset(dataset_id, db, user)
    rules = (
        db.query(ValidationRule).filter_by(dataset_id=dataset_id)
        .order_by(ValidationRule.id).all()
    )
    latest_results: dict[int, RuleResult] = {}
    for result in (db.query(RuleResult).filter_by(dataset_id=dataset_id)
                   .order_by(desc(RuleResult.run_at)).all()):
        latest_results.setdefault(result.rule_id, result)
    return [{
        "id": r.id,
        "column_name": r.column_name,
        "rule_type": r.rule_type,
        "rule_label": RULE_TYPES.get(r.rule_type, r.rule_type),
        "params": r.params,
        "description": r.description,
        "source": r.source,
        "enabled": r.enabled,
        "last_result": ({
            "checked": latest_results[r.id].checked,
            "violations": latest_results[r.id].violations,
            "samples": latest_results[r.id].sample_violations,
            "run_at": latest_results[r.id].run_at.isoformat(),
        } if r.id in latest_results else None),
    } for r in rules]


@router.post("/datasets/{dataset_id}/rules")
def create_rule(dataset_id: int, body: RuleCreate, db: Session = Depends(get_db),
                user: User = Depends(require_writer)):
    _get_dataset(dataset_id, db, user)
    if body.rule_type not in RULE_TYPES:
        raise HTTPException(400, f"rule_type harus salah satu dari: {', '.join(RULE_TYPES)}")
    rule = ValidationRule(
        dataset_id=dataset_id,
        column_name=body.column_name,
        rule_type=body.rule_type,
        params=body.params or {},
        description=body.description or RULE_TYPES[body.rule_type],
        source="ai" if body.source == "ai" else "manual",
        enabled=True,
    )
    db.add(rule)
    db.commit()
    return {"id": rule.id}


@router.get("/llm-status")
def llm_status():
    return {"available": llm_available()}


@router.post("/datasets/{dataset_id}/rules/generate")
def generate_rule_nl(dataset_id: int, body: RuleGenerate, db: Session = Depends(get_db),
                     user: User = Depends(require_writer)):
    """NL Rule Generation (F4): instruksi bahasa natural -> proposal rule terstruktur.

    Proposal TIDAK langsung disimpan — user meninjau dulu lalu menyimpan lewat
    POST /datasets/{id}/rules dengan source="ai" (sesuai acceptance criteria F4)."""
    _get_dataset(dataset_id, db, user)
    if not body.instruction.strip():
        raise HTTPException(400, "Instruksi tidak boleh kosong")

    columns = _column_info(db, dataset_id)
    column_info = [{
        "name": c.name,
        "inferred_type": c.inferred_type,
        "sample_values": [t["value"] for t in (c.top_values or [])[:3]],
    } for c in columns]

    try:
        proposal = generate_rule(body.instruction, column_info)
    except LLMNotConfigured as exc:
        raise HTTPException(503, str(exc))
    except Exception as exc:  # noqa: BLE001 - respons LLM/jaringan tak terduga
        raise HTTPException(502, f"Gagal generate rule dari LLM: {exc}")

    return _validate_proposal(proposal, {c.name for c in columns})


@router.post("/datasets/{dataset_id}/rules/suggest")
def suggest_rules_from_schema(dataset_id: int, db: Session = Depends(get_db),
                              user: User = Depends(require_writer)):
    """Auto-Suggest Rule dari skema (F4 acceptance criteria — LLM menyarankan tanpa
    diminta instruksi spesifik). Proposal TIDAK langsung disimpan — sama seperti NL
    generation, user meninjau dan mengaktifkan satu per satu lewat POST rules biasa."""
    _get_dataset(dataset_id, db, user)
    columns = _column_info(db, dataset_id)
    column_info = [{
        "name": c.name,
        "inferred_type": c.inferred_type,
        "sample_values": [t["value"] for t in (c.top_values or [])[:3]],
    } for c in columns]
    existing = [(r.column_name, r.rule_type) for r in
                db.query(ValidationRule).filter_by(dataset_id=dataset_id).all()]

    try:
        proposals = suggest_rules(column_info, existing)
    except LLMNotConfigured as exc:
        raise HTTPException(503, str(exc))
    except Exception as exc:  # noqa: BLE001 - respons LLM/jaringan tak terduga
        raise HTTPException(502, f"Gagal menyarankan rule dari LLM: {exc}")

    valid_columns = {c.name for c in columns}
    validated = []
    for proposal in proposals:
        try:
            validated.append(_validate_proposal(proposal, valid_columns))
        except HTTPException:
            continue  # lewati satu saran yang tidak valid, jangan gagalkan semua
    return validated


@router.patch("/rules/{rule_id}")
def update_rule(rule_id: int, body: RuleUpdate, db: Session = Depends(get_db),
                user: User = Depends(require_writer)):
    rule = db.get(ValidationRule, rule_id)
    if rule is None:
        raise HTTPException(404, "Rule tidak ditemukan")
    _get_dataset(rule.dataset_id, db, user)
    rule.enabled = body.enabled
    db.commit()
    return {"id": rule.id, "enabled": rule.enabled}


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db),
                user: User = Depends(require_writer)):
    rule = db.get(ValidationRule, rule_id)
    if rule is None:
        raise HTTPException(404, "Rule tidak ditemukan")
    _get_dataset(rule.dataset_id, db, user)
    db.query(RuleResult).filter_by(rule_id=rule.id).delete()
    db.delete(rule)
    db.commit()
    return {"deleted": True}


@router.post("/datasets/{dataset_id}/rules/rerun")
def rerun(dataset_id: int, db: Session = Depends(get_db),
          user: User = Depends(require_writer)):
    """Untuk dataset upload: re-validasi rule saja. Untuk dataset dari koneksi database
    (backlog #2): tarik ulang data terbaru dari sumbernya dulu baru diproses penuh."""
    dataset = _get_dataset(dataset_id, db, user)
    if dataset.status not in ("ready", "error"):
        raise HTTPException(409, "Dataset masih diproses")
    enqueue_refresh_dataset(dataset_id)
    return {"queued": True}

class DedupRule(BaseModel):
    column: str
    method: str

class DedupConfigUpdate(BaseModel):
    threshold: float
    rules: list[DedupRule]

@router.get("/datasets/{dataset_id}/dedup-config")
def get_dedup_config(dataset_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    dataset = _get_dataset(dataset_id, db, user)
    return dataset.dedup_config or {}

@router.put("/datasets/{dataset_id}/dedup-config")
def update_dedup_config(dataset_id: int, body: DedupConfigUpdate, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    dataset = _get_dataset(dataset_id, db, user)
    

        
    dataset.dedup_config = body.model_dump()
    db.commit()
    
    # Trigger ulang kalkulasi cluster karena rule deduplikasi berubah
    enqueue_refresh_dataset(dataset.id, db)
    return dataset.dedup_config

