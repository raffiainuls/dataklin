from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    Dataset,
    DatasetColumn,
    EntityCluster,
    Pipeline,
    RecordMatchScore,
    RuleResult,
    User,
    ValidationRule,
)
from ..security import get_current_user, require_writer
from ..services import storage
from ..services.entity_resolution import calibrate_threshold, json_safe_record
from ..services.llm import LLMNotConfigured, generate_rule, llm_available, suggest_rules
from ..services.loader import load_dataframe
from ..services.rule_engine import (
    RULE_TYPES,
    validate_rule_config,
)
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
    if not isinstance(proposal, dict):
        raise HTTPException(502, "LLM harus mengembalikan satu object JSON rule")
    rule_type = proposal.get("rule_type")
    if rule_type not in RULE_TYPES:
        raise HTTPException(502, f"LLM mengembalikan rule_type tidak dikenal: {rule_type}")
    raw_params = proposal.get("params")
    if raw_params is not None and not isinstance(raw_params, dict):
        raise HTTPException(502, "LLM mengembalikan params yang bukan object JSON")
    params = raw_params or {}
    _validate_rule_params(rule_type, params, 502)
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


def _validate_rule_params(rule_type: str, params: dict, status_code: int = 400) -> None:
    try:
        validate_rule_config(rule_type, params)
    except ValueError as exc:
        raise HTTPException(status_code, str(exc)) from exc


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


@router.get("/datasets/{dataset_id}/rules/{rule_id}/violations")
def list_rule_violations(dataset_id: int, rule_id: int,
                         page: int = Query(1, ge=1),
                         page_size: int = Query(50, ge=1, le=200),
                         db: Session = Depends(get_db),
                         user: User = Depends(get_current_user)):
    dataset = _get_dataset(dataset_id, db, user)
    rule = db.get(ValidationRule, rule_id)
    if rule is None or rule.dataset_id != dataset.id:
        raise HTTPException(404, "Rule tidak ditemukan")

    result = (db.query(RuleResult)
              .filter_by(dataset_id=dataset.id, rule_id=rule.id)
              .order_by(desc(RuleResult.run_at)).first())
    if result is None:
        return {
            "dataset": {"id": dataset.id, "name": dataset.name},
            "rule": {"id": rule.id, "column_name": rule.column_name,
                     "description": rule.description or RULE_TYPES.get(rule.rule_type)},
            "columns": [],
            "total": 0,
            "stored_total": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 1,
            "run_at": None,
            "rows": [],
        }

    content = storage.get_object(dataset.storage_key)
    dataframe = load_dataframe(content, dataset.filename)
    violations = result.sample_violations or []
    offset = (page - 1) * page_size
    rows = []
    for violation in violations[offset:offset + page_size]:
        row_index = violation.get("row")
        if not isinstance(row_index, int) or row_index not in dataframe.index:
            continue
        rows.append({
            "row": row_index,
            "failed_value": violation.get("value"),
            "data": json_safe_record(dataframe.loc[row_index].to_dict()),
        })

    return {
        "dataset": {"id": dataset.id, "name": dataset.name},
        "rule": {
            "id": rule.id,
            "column_name": rule.column_name,
            "rule_type": rule.rule_type,
            "description": rule.description or RULE_TYPES.get(rule.rule_type),
        },
        "columns": [str(column) for column in dataframe.columns],
        "total": result.violations,
        "stored_total": len(violations),
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (len(violations) + page_size - 1) // page_size),
        "run_at": result.run_at.isoformat(),
        "rows": rows,
    }


@router.post("/datasets/{dataset_id}/rules")
def create_rule(dataset_id: int, body: RuleCreate, db: Session = Depends(get_db),
                user: User = Depends(require_writer)):
    _get_dataset(dataset_id, db, user)
    valid_columns = {column.name for column in _column_info(db, dataset_id)}
    if body.rule_type not in RULE_TYPES:
        raise HTTPException(400, f"rule_type harus salah satu dari: {', '.join(RULE_TYPES)}")
    rule_type = body.rule_type
    params = body.params or {}
    _validate_rule_params(rule_type, params)
    if rule_type == "cross_column":
        if params.get("left") not in valid_columns or params.get("right") not in valid_columns:
            raise HTTPException(400, "Rule merujuk kolom yang tidak ada di dataset")
        column_name = params["left"]
    else:
        if body.column_name not in valid_columns:
            raise HTTPException(400, f"Kolom tidak ditemukan: {body.column_name}")
        column_name = body.column_name
    rule = ValidationRule(
        dataset_id=dataset_id,
        column_name=column_name,
        rule_type=rule_type,
        params=params,
        description=body.description or RULE_TYPES[rule_type],
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

    pipeline = (db.query(Pipeline)
                .filter_by(org_id=user.org_id, dataset_id=dataset.id)
                .order_by(desc(Pipeline.created_at)).first())
    if pipeline is None:
        pipeline = Pipeline(
            org_id=user.org_id,
            dataset_id=dataset.id,
            name=f"Validasi {dataset.name}",
            enable_profiling=True,
            enable_deduplication=True,
            schedule="manual",
            created_by=user.email,
        )
        db.add(pipeline)
        db.flush()

    previous_status = dataset.status
    previous_pipeline_status = pipeline.last_run_status
    previous_pipeline_run_at = pipeline.last_run_at
    dataset.status = "queued"
    dataset.error_message = None
    pipeline.last_run_status = "running"
    pipeline.last_run_at = datetime.utcnow()
    pipeline.last_run_message = None
    db.commit()
    try:
        enqueue_refresh_dataset(dataset_id, pipeline.id)
    except Exception as exc:
        dataset.status = previous_status
        dataset.error_message = "Gagal menjadwalkan validasi"
        pipeline.last_run_status = previous_pipeline_status
        pipeline.last_run_at = previous_pipeline_run_at
        pipeline.last_run_message = "Gagal menjadwalkan validasi"
        db.commit()
        raise HTTPException(503, "Gagal menjadwalkan validasi") from exc
    return {"queued": True, "pipeline_id": pipeline.id}

MATCH_METHODS = {
    "exact", "fuzzy_ratio", "token_sort", "token_set", "jaro_winkler",
    "phonetic", "phone", "email", "composite_exact",
}
BLOCK_METHODS = {
    "exact", "composite_exact", "prefix", "token_prefix", "phonetic",
    "ngram", "email_local", "phone_suffix",
}
NORMALIZER_TYPES = {"basic", "name", "phone", "email", "address", "identifier", "date"}


class DedupRule(BaseModel):
    column: str | None = None
    columns: list[str] = Field(default_factory=list)
    method: str = "exact"
    weight: float = Field(default=2.0, ge=0, le=5)
    normalizers: list[str] = Field(default_factory=list)
    mismatch_penalty: float = Field(default=0.0, ge=0, le=1)
    mismatch_threshold: float = Field(default=0.2, ge=0, le=1)
    required: bool = False
    required_threshold: float = Field(default=0.999, ge=0, le=1)
    m_probability: float = Field(default=0.95, gt=0.5, lt=1)

    @model_validator(mode="after")
    def validate_rule(self):
        if self.method not in MATCH_METHODS:
            raise ValueError(f"Metode matching tidak didukung: {self.method}")
        selected = self.columns or ([self.column] if self.column else [])
        if not selected:
            raise ValueError("Rule matching membutuhkan column atau columns")
        if self.method == "composite_exact" and len(selected) < 2:
            raise ValueError("composite_exact membutuhkan minimal dua kolom")
        invalid = set(self.normalizers) - NORMALIZER_TYPES
        if invalid:
            raise ValueError(f"Normalizer tidak didukung: {', '.join(sorted(invalid))}")
        return self


class DedupBlockingRule(BaseModel):
    column: str | None = None
    columns: list[str] = Field(default_factory=list)
    method: str = "exact"
    normalizers: list[str] = Field(default_factory=list)
    length: int = Field(default=3, ge=1, le=20)

    @model_validator(mode="after")
    def validate_rule(self):
        if self.method not in BLOCK_METHODS:
            raise ValueError(f"Metode blocking tidak didukung: {self.method}")
        selected = self.columns or ([self.column] if self.column else [])
        if not selected:
            raise ValueError("Blocking rule membutuhkan column atau columns")
        if self.method == "composite_exact" and len(selected) < 2:
            raise ValueError("composite_exact membutuhkan minimal dua kolom")
        invalid = set(self.normalizers) - NORMALIZER_TYPES
        if invalid:
            raise ValueError(f"Normalizer tidak didukung: {', '.join(sorted(invalid))}")
        return self


class ExactMatchRule(BaseModel):
    columns: list[str] = Field(min_length=1)
    normalizers: list[str] = Field(default_factory=lambda: ["basic"])

    @model_validator(mode="after")
    def validate_normalizers(self):
        invalid = set(self.normalizers) - NORMALIZER_TYPES
        if invalid:
            raise ValueError(f"Normalizer tidak didukung: {', '.join(sorted(invalid))}")
        return self


class ClusterValidationConfig(BaseModel):
    enabled: bool = True
    method: str = "representative"
    min_cohesion: float = Field(default=0.7, ge=0, le=1)
    min_representative_score: float = Field(default=0.75, ge=0, le=1)

    @model_validator(mode="after")
    def validate_method(self):
        if self.method not in {"connected", "representative"}:
            raise ValueError("cluster_validation.method harus connected atau representative")
        return self


class DedupConfigUpdate(BaseModel):
    version: int = 2
    threshold: float = Field(default=0.8, ge=0.1, le=1)
    prior_probability: float = Field(default=0.05, gt=0, le=0.5)
    exact_row_match: bool = True
    rules: list[DedupRule] = Field(default_factory=list)
    blocking_rules: list[DedupBlockingRule] = Field(default_factory=list)
    exact_match_rules: list[ExactMatchRule] = Field(default_factory=list)
    cluster_validation: ClusterValidationConfig = Field(default_factory=ClusterValidationConfig)

@router.get("/datasets/{dataset_id}/dedup-config")
def get_dedup_config(dataset_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    dataset = _get_dataset(dataset_id, db, user)
    return dataset.dedup_config or {}


@router.get("/datasets/{dataset_id}/dedup-config/calibration")
def dedup_threshold_calibration(dataset_id: int, db: Session = Depends(get_db),
                                user: User = Depends(get_current_user)):
    dataset = _get_dataset(dataset_id, db, user)
    rows = (
        db.query(RecordMatchScore.score, EntityCluster.status)
        .join(EntityCluster, RecordMatchScore.cluster_id == EntityCluster.id)
        .filter(
            EntityCluster.dataset_id == dataset.id,
            EntityCluster.status.in_(("confirmed", "split")),
        )
        .all()
    )
    labeled_scores = [(float(score), status == "confirmed") for score, status in rows]
    return calibrate_threshold(labeled_scores)

@router.put("/datasets/{dataset_id}/dedup-config")
def update_dedup_config(dataset_id: int, body: DedupConfigUpdate, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    dataset = _get_dataset(dataset_id, db, user)
    available_columns = {column.name for column in _column_info(db, dataset.id)}
    referenced_columns = set()
    for rule in [*body.rules, *body.blocking_rules]:
        referenced_columns.update(rule.columns or ([rule.column] if rule.column else []))
    for rule in body.exact_match_rules:
        referenced_columns.update(rule.columns)
    unknown_columns = referenced_columns - available_columns
    if unknown_columns:
        raise HTTPException(
            400, f"Kolom konfigurasi dedup tidak ditemukan: {', '.join(sorted(unknown_columns))}")

    previous_config = dataset.dedup_config
    dataset.dedup_config = body.model_dump()
    db.commit()

    # Trigger ulang kalkulasi cluster karena rule deduplikasi berubah
    try:
        enqueue_refresh_dataset(dataset.id)
    except Exception as exc:
        dataset.dedup_config = previous_config
        db.commit()
        raise HTTPException(
            503, "Konfigurasi tidak disimpan karena kalkulasi ulang gagal dijadwalkan") from exc
    return dataset.dedup_config
