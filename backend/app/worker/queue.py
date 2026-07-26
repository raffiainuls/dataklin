from redis import Redis
from rq import Queue

from ..config import settings


def get_queue() -> Queue:
    return Queue("dataqc", connection=Redis.from_url(settings.redis_url))


def enqueue_process_dataset(dataset_id: int) -> None:
    get_queue().enqueue("app.worker.tasks.process_dataset", dataset_id, job_timeout=3600)


def enqueue_refresh_dataset(dataset_id: int) -> None:
    """Dispatcher source-aware: upload -> rerun_rules, koneksi database -> tarik ulang
    data terbaru + proses penuh (backlog #2)."""
    get_queue().enqueue("app.worker.tasks.refresh_dataset", dataset_id, job_timeout=3600)
