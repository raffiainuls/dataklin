from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Alert, Dataset, Organization, QualityScoreHistory, User
from ..security import Actor, get_current_user, get_org_reader, require_writer

router = APIRouter(tags=["monitoring"])


@router.get("/datasets/{dataset_id}/history")
def score_history(dataset_id: int, db: Session = Depends(get_db),
                  user: Actor = Depends(get_org_reader)):
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or dataset.org_id != user.org_id:
        raise HTTPException(404, "Dataset tidak ditemukan")
    history = (
        db.query(QualityScoreHistory).filter_by(dataset_id=dataset_id)
        .order_by(QualityScoreHistory.created_at).all()
    )
    return [{
        "score": h.score,
        "dimensions": h.dimensions,
        "created_at": h.created_at.isoformat(),
    } for h in history]


class MonitoringUpdate(BaseModel):
    enabled: bool
    interval_minutes: int = 1440


@router.put("/datasets/{dataset_id}/monitoring")
def update_monitoring(dataset_id: int, body: MonitoringUpdate, db: Session = Depends(get_db),
                      user: User = Depends(require_writer)):
    """Drift monitoring terjadwal (F10): re-validasi rule + hitung ulang skor secara
    berkala tanpa perlu diklik manual, supaya efek review cluster/perubahan rule ikut
    terpantau dari waktu ke waktu."""
    from ..worker.scheduler import cancel_monitoring, schedule_monitoring

    dataset = db.get(Dataset, dataset_id)
    if dataset is None or dataset.org_id != user.org_id:
        raise HTTPException(404, "Dataset tidak ditemukan")
    if body.enabled and not 5 <= body.interval_minutes <= 43200:
        raise HTTPException(400, "Interval harus antara 5 menit dan 30 hari")

    cancel_monitoring(dataset.monitoring_job_id)
    if body.enabled:
        dataset.monitoring_job_id = schedule_monitoring(dataset.id, body.interval_minutes)
        dataset.monitoring_interval_minutes = body.interval_minutes
    else:
        dataset.monitoring_job_id = None
    dataset.monitoring_enabled = body.enabled
    db.commit()
    return {
        "monitoring_enabled": dataset.monitoring_enabled,
        "monitoring_interval_minutes": dataset.monitoring_interval_minutes,
    }


@router.get("/alerts")
def list_alerts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    alerts = (
        db.query(Alert).filter_by(org_id=user.org_id)
        .order_by(desc(Alert.created_at)).limit(50).all()
    )
    dataset_names = {d.id: d.name for d in db.query(Dataset).filter_by(org_id=user.org_id)}
    return [{
        "id": a.id,
        "dataset_id": a.dataset_id,
        "dataset_name": dataset_names.get(a.dataset_id, "-"),
        "alert_type": a.alert_type,
        "severity": a.severity,
        "message": a.message,
        "status": a.status,
        "created_at": a.created_at.isoformat(),
    } for a in alerts]


@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: int, db: Session = Depends(get_db),
                  user: User = Depends(require_writer)):
    alert = db.get(Alert, alert_id)
    if alert is None or alert.org_id != user.org_id:
        raise HTTPException(404, "Alert tidak ditemukan")
    alert.status = "resolved"
    db.commit()
    return {"status": "resolved"}


class ThresholdUpdate(BaseModel):
    alert_threshold: int


class NotificationSettings(BaseModel):
    webhook_url: str = ""
    slack_webhook_url: str = ""
    notify_emails: str = ""


def _settings_dict(org: Organization) -> dict:
    return {
        "organization": org.name,
        "alert_threshold": org.alert_threshold,
        "webhook_url": org.webhook_url or "",
        "slack_webhook_url": org.slack_webhook_url or "",
        "notify_emails": org.notify_emails or "",
    }


@router.get("/settings")
def get_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    org = db.get(Organization, user.org_id)
    return _settings_dict(org)


@router.put("/settings")
def update_settings(body: ThresholdUpdate, db: Session = Depends(get_db),
                    user: User = Depends(require_writer)):
    if not 0 <= body.alert_threshold <= 100:
        raise HTTPException(400, "Threshold harus 0-100")
    org = db.get(Organization, user.org_id)
    org.alert_threshold = body.alert_threshold
    db.commit()
    return {"alert_threshold": org.alert_threshold}


@router.put("/settings/notifications")
def update_notification_settings(body: NotificationSettings, db: Session = Depends(get_db),
                                 user: User = Depends(require_writer)):
    org = db.get(Organization, user.org_id)
    org.webhook_url = body.webhook_url.strip() or None
    org.slack_webhook_url = body.slack_webhook_url.strip() or None
    org.notify_emails = body.notify_emails.strip() or None
    db.commit()
    return _settings_dict(org)


@router.post("/settings/notifications/test")
def test_notification(db: Session = Depends(get_db), user: User = Depends(require_writer)):
    """Kirim notifikasi uji ke semua channel yang terkonfigurasi dan laporkan hasil
    per-channel apa adanya, supaya user tahu konfigurasinya benar-benar berhasil atau
    tidak tanpa perlu menunggu alert asli terjadi."""
    from ..services.notifier import _dispatch

    org = db.get(Organization, user.org_id)
    if not (org.webhook_url or org.slack_webhook_url or org.notify_emails):
        raise HTTPException(400, "Belum ada channel notifikasi yang dikonfigurasi")
    results = _dispatch(
        org,
        "[Dataklin] Notifikasi Uji",
        f"Ini pesan uji dari Dataklin, dikirim oleh {user.email}. "
        "Jika Anda menerima ini, konfigurasi notifikasi sudah benar.",
        {"event": "test", "sent_by": user.email},
    )
    return {
        channel: ("berhasil" if status is True else "tidak dikonfigurasi" if status is None
                 else f"gagal: {status}")
        for channel, status in results.items()
    }
