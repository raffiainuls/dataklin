"""Penjadwal drift monitoring (F10): re-validasi berkala per dataset lewat rq-scheduler.

Container terpisah `rqscheduler` (lihat docker-compose.yml) memoles registry ini dan
meng-enqueue job ke queue "dataqc" yang sama dipakai worker biasa saat waktunya tiba.
Menjadwalkan `refresh_dataset` (dispatcher source-aware, lihat worker/tasks.py) alih-alih
`rerun_rules` langsung — supaya dataset dari koneksi database (backlog #2) genuinely
menarik data terbaru tiap siklus, bukan cuma re-validasi cache statis.
"""
from __future__ import annotations

from datetime import datetime, timezone

from redis import Redis
from rq_scheduler import Scheduler

from ..config import settings


def _get_scheduler() -> Scheduler:
    return Scheduler(queue_name="dataqc", connection=Redis.from_url(settings.redis_url))


def schedule_monitoring(dataset_id: int, interval_minutes: int) -> str:
    """Jadwalkan refresh_dataset berulang setiap interval_minutes; kembalikan job_id."""
    scheduler = _get_scheduler()
    job = scheduler.schedule(
        scheduled_time=datetime.now(timezone.utc),
        func="app.worker.tasks.refresh_dataset",
        args=[dataset_id],
        interval=interval_minutes * 60,
        repeat=None,
        id=f"monitor-dataset-{dataset_id}",
    )
    return job.id


def cancel_monitoring(job_id: str | None) -> None:
    if not job_id:
        return
    try:
        _get_scheduler().cancel(job_id)
    except Exception:  # noqa: BLE001 - job mungkin sudah tidak ada, aman diabaikan
        pass
