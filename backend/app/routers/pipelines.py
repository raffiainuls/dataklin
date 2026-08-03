from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Dataset, Pipeline, User
from ..security import get_current_user, require_writer
from ..worker.queue import enqueue_run_pipeline
from ..worker.scheduler import cancel_pipeline, schedule_pipeline

router = APIRouter(prefix="/pipelines", tags=["pipelines"])

# manual = tanpa jadwal otomatis, hanya lewat tombol "Run Now"
SCHEDULE_INTERVAL_MINUTES = {"hourly": 60, "daily": 1440, "weekly": 10080}


def _pipeline_dict(pipeline: Pipeline, dataset_name: str | None) -> dict:
    return {
        "id": pipeline.id,
        "name": pipeline.name,
        "dataset_id": pipeline.dataset_id,
        "dataset_name": dataset_name,
        "enable_profiling": pipeline.enable_profiling,
        "enable_deduplication": pipeline.enable_deduplication,
        "schedule": pipeline.schedule,
        "last_run_at": pipeline.last_run_at.isoformat() if pipeline.last_run_at else None,
        "last_run_status": pipeline.last_run_status,
        "last_run_message": pipeline.last_run_message,
        "created_by": pipeline.created_by,
        "created_at": pipeline.created_at.isoformat(),
    }


def _apply_schedule(pipeline: Pipeline, schedule: str) -> None:
    """Batalkan job lama (bila ada) lalu jadwalkan ulang sesuai schedule baru."""
    cancel_pipeline(pipeline.schedule_job_id)
    interval = SCHEDULE_INTERVAL_MINUTES.get(schedule)
    pipeline.schedule = schedule
    pipeline.schedule_job_id = schedule_pipeline(pipeline.id, interval) if interval else None


@router.get("")
def list_pipelines(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    pipelines = (db.query(Pipeline).filter_by(org_id=user.org_id)
                 .order_by(desc(Pipeline.created_at)).all())
    dataset_names = {d.id: d.name for d in db.query(Dataset).filter_by(org_id=user.org_id)}
    return [_pipeline_dict(p, dataset_names.get(p.dataset_id)) for p in pipelines]


class PipelineCreate(BaseModel):
    name: str
    dataset_id: int
    enable_profiling: bool = True
    enable_deduplication: bool = False
    schedule: str = "manual"


@router.post("")
def create_pipeline(body: PipelineCreate, db: Session = Depends(get_db),
                    user: User = Depends(require_writer)):
    if not body.name.strip():
        raise HTTPException(400, "Nama pipeline tidak boleh kosong")
    if not (body.enable_profiling or body.enable_deduplication):
        raise HTTPException(400, "Pilih minimal satu opsi pemrosesan")
    if body.schedule not in ("manual", *SCHEDULE_INTERVAL_MINUTES):
        raise HTTPException(400, "Jadwal tidak valid")
    dataset = db.get(Dataset, body.dataset_id)
    if dataset is None or dataset.org_id != user.org_id:
        raise HTTPException(404, "Dataset tidak ditemukan")

    pipeline = Pipeline(org_id=user.org_id, dataset_id=dataset.id, name=body.name.strip(),
                        enable_profiling=body.enable_profiling,
                        enable_deduplication=body.enable_deduplication,
                        created_by=user.email)
    db.add(pipeline)
    db.flush()
    _apply_schedule(pipeline, body.schedule)
    db.commit()
    return _pipeline_dict(pipeline, dataset.name)


def _get_owned_pipeline(pipeline_id: int, db: Session, user: User) -> Pipeline:
    pipeline = db.get(Pipeline, pipeline_id)
    if pipeline is None or pipeline.org_id != user.org_id:
        raise HTTPException(404, "Pipeline tidak ditemukan")
    return pipeline


@router.get("/{pipeline_id}")
def get_pipeline(pipeline_id: int, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    pipeline = _get_owned_pipeline(pipeline_id, db, user)
    dataset = db.get(Dataset, pipeline.dataset_id)
    return _pipeline_dict(pipeline, dataset.name if dataset else None)


class PipelineUpdate(BaseModel):
    name: str
    enable_profiling: bool = True
    enable_deduplication: bool = False
    schedule: str = "manual"


@router.patch("/{pipeline_id}")
def update_pipeline(pipeline_id: int, body: PipelineUpdate, db: Session = Depends(get_db),
                    user: User = Depends(require_writer)):
    pipeline = _get_owned_pipeline(pipeline_id, db, user)
    if not body.name.strip():
        raise HTTPException(400, "Nama pipeline tidak boleh kosong")
    if not (body.enable_profiling or body.enable_deduplication):
        raise HTTPException(400, "Pilih minimal satu opsi pemrosesan")
    if body.schedule not in ("manual", *SCHEDULE_INTERVAL_MINUTES):
        raise HTTPException(400, "Jadwal tidak valid")

    pipeline.name = body.name.strip()
    pipeline.enable_profiling = body.enable_profiling
    pipeline.enable_deduplication = body.enable_deduplication
    if body.schedule != pipeline.schedule:
        _apply_schedule(pipeline, body.schedule)
    db.commit()
    dataset = db.get(Dataset, pipeline.dataset_id)
    return _pipeline_dict(pipeline, dataset.name if dataset else None)


@router.delete("/{pipeline_id}")
def delete_pipeline(pipeline_id: int, db: Session = Depends(get_db),
                    user: User = Depends(require_writer)):
    pipeline = _get_owned_pipeline(pipeline_id, db, user)
    cancel_pipeline(pipeline.schedule_job_id)
    db.delete(pipeline)
    db.commit()
    return {"deleted": True}


@router.post("/{pipeline_id}/run")
def run_pipeline_now(pipeline_id: int, db: Session = Depends(get_db),
                     user: User = Depends(require_writer)):
    pipeline = _get_owned_pipeline(pipeline_id, db, user)
    dataset = db.get(Dataset, pipeline.dataset_id)
    if dataset is None:
        raise HTTPException(404, "Dataset sumber pipeline ini sudah dihapus")
    dataset.status = "queued"
    db.commit()
    enqueue_run_pipeline(pipeline.id)
    return {"queued": True}
