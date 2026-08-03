import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .config import settings
from .db import Base, SessionLocal, engine
from .models import Organization, User
from .routers import (
    api_keys,
    auth,
    clusters,
    connections,
    cross_dataset,
    datasets,
    monitoring,
    pipelines,
    rules,
    scorecard,
)
from .security import hash_password
from .services import storage

app = FastAPI(title="Dataklin API", version="0.1.0",
              description="Data Quality & Entity Resolution Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(datasets.router)
app.include_router(rules.router)
app.include_router(clusters.router)
app.include_router(scorecard.router)
app.include_router(monitoring.router)
app.include_router(api_keys.router)
app.include_router(connections.router)
app.include_router(cross_dataset.router)
app.include_router(pipelines.router)


def _wait_for_db(retries: int = 30) -> None:
    for attempt in range(retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2)


def _seed() -> None:
    db = SessionLocal()
    try:
        org = db.query(Organization).first()
        if org is None:
            org = Organization(name="Dataklin Demo",
                               alert_threshold=settings.default_alert_threshold)
            db.add(org)
            db.flush()
        admin = db.query(User).filter_by(email=settings.admin_email).first()
        if admin is None:
            db.add(User(
                org_id=org.id,
                email=settings.admin_email,
                name=settings.admin_name,
                password_hash=hash_password(settings.admin_password),
                role="admin",
            ))
        db.commit()
    finally:
        db.close()


@app.on_event("startup")
def startup() -> None:
    _wait_for_db()
    with engine.connect() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        except Exception:
            conn.rollback()  # pgvector opsional; dipakai saat embedding ER diaktifkan
    Base.metadata.create_all(engine)
    # migrasi ringan untuk kolom yang ditambahkan setelah rilis awal
    with engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE datasets ADD COLUMN IF NOT EXISTS survivorship_config JSON"))
        conn.execute(text(
            "ALTER TABLE datasets ADD COLUMN IF NOT EXISTS pii_findings JSON"))
        conn.execute(text(
            "ALTER TABLE datasets ADD COLUMN IF NOT EXISTS monitoring_enabled "
            "BOOLEAN DEFAULT FALSE"))
        conn.execute(text(
            "ALTER TABLE datasets ADD COLUMN IF NOT EXISTS monitoring_interval_minutes "
            "INTEGER DEFAULT 1440"))
        conn.execute(text(
            "ALTER TABLE datasets ADD COLUMN IF NOT EXISTS monitoring_job_id VARCHAR(64)"))
        conn.execute(text(
            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS webhook_url VARCHAR(500)"))
        conn.execute(text(
            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS slack_webhook_url VARCHAR(500)"))
        conn.execute(text(
            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS notify_emails VARCHAR(500)"))
        conn.execute(text(
            "ALTER TABLE datasets ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) "
            "DEFAULT 'upload'"))
        conn.execute(text(
            "ALTER TABLE datasets ADD COLUMN IF NOT EXISTS connection_id INTEGER"))
        conn.execute(text(
            "ALTER TABLE datasets ADD COLUMN IF NOT EXISTS source_query TEXT"))
        conn.execute(text(
            "ALTER TABLE cross_dataset_rules ADD COLUMN IF NOT EXISTS check_type "
            "VARCHAR(30) DEFAULT 'referential_integrity'"))
        conn.execute(text(
            "ALTER TABLE cross_dataset_rules ADD COLUMN IF NOT EXISTS primary_value_column "
            "VARCHAR(255)"))
        conn.execute(text(
            "ALTER TABLE cross_dataset_rules ADD COLUMN IF NOT EXISTS "
            "reference_value_column VARCHAR(255)"))
        conn.commit()
    _seed()
    for attempt in range(10):
        try:
            storage.ensure_bucket()
            break
        except Exception:
            time.sleep(2)


@app.get("/health")
def health():
    return {"status": "ok", "app": "dataklin"}
