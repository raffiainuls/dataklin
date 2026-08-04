from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    alert_threshold: Mapped[int] = mapped_column(Integer, default=75)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # Notifikasi multi-channel (F10/F12, backlog #29) — kosong = channel nonaktif graceful
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    slack_webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notify_emails: Mapped[str | None] = mapped_column(String(500), nullable=True)

    users: Mapped[list["User"]] = relationship(back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="admin")  # admin|analyst|viewer
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    organization: Mapped[Organization] = relationship(back_populates="users")


class DataConnection(Base):
    """Koneksi database langsung (backlog #2) — sumber dataset alternatif selain upload
    file. Password dienkripsi at-rest (Fernet), tidak pernah dikembalikan lewat API."""
    __tablename__ = "data_connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    name: Mapped[str] = mapped_column(String(200))
    db_type: Mapped[str] = mapped_column(String(20))  # postgresql | mysql
    host: Mapped[str] = mapped_column(String(255))
    port: Mapped[int] = mapped_column(Integer)
    database: Mapped[str] = mapped_column(String(255))
    username: Mapped[str] = mapped_column(String(255))
    password_encrypted: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    name: Mapped[str] = mapped_column(String(255))
    filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(500))
    # upload | database — sumber ingestion (backlog #2)
    source_type: Mapped[str] = mapped_column(String(20), default="upload")
    connection_id: Mapped[int | None] = mapped_column(
        ForeignKey("data_connections.id"), nullable=True)
    source_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    # queued | processing | ready | error
    status: Mapped[str] = mapped_column(String(30), default="queued")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    column_count: Mapped[int] = mapped_column(Integer, default=0)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    dimensions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # {threshold: float, rules: [{column: str, method: str, weight: float}]} — konfigurasi rule dedup
    dedup_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # {column: {strategy, params}} — aturan survivorship default per kolom (F7)
    survivorship_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # [{column_name, pii_type, pii_label, masking, sample_masked}] — deteksi PII (F11)
    pii_findings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Drift monitoring terjadwal (F10)
    monitoring_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    monitoring_interval_minutes: Mapped[int] = mapped_column(Integer, default=1440)
    monitoring_job_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    columns: Mapped[list["DatasetColumn"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )


class DatasetColumn(Base):
    __tablename__ = "dataset_columns"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"))
    name: Mapped[str] = mapped_column(String(255))
    position: Mapped[int] = mapped_column(Integer, default=0)
    inferred_type: Mapped[str] = mapped_column(String(30), default="text")
    completeness: Mapped[float] = mapped_column(Float, default=0)
    uniqueness: Mapped[float | None] = mapped_column(Float, nullable=True)
    validity: Mapped[float | None] = mapped_column(Float, nullable=True)
    consistency: Mapped[float | None] = mapped_column(Float, nullable=True)
    null_count: Mapped[int] = mapped_column(Integer, default=0)
    unique_count: Mapped[int] = mapped_column(Integer, default=0)
    top_values: Mapped[list | None] = mapped_column(JSON, nullable=True)
    stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    dataset: Mapped[Dataset] = relationship(back_populates="columns")


class ValidationRule(Base):
    __tablename__ = "validation_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"))
    column_name: Mapped[str] = mapped_column(String(255))
    rule_type: Mapped[str] = mapped_column(String(50))
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    description: Mapped[str] = mapped_column(String(500), default="")
    source: Mapped[str] = mapped_column(String(20), default="builtin")  # builtin|manual|ai
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class RuleResult(Base):
    __tablename__ = "rule_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("validation_rules.id"))
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"))
    checked: Mapped[int] = mapped_column(Integer, default=0)
    violations: Mapped[int] = mapped_column(Integer, default=0)
    sample_violations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    run_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class RecordMatchScore(Base):
    __tablename__ = "record_match_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"))
    cluster_id: Mapped[int | None] = mapped_column(ForeignKey("entity_clusters.id"), nullable=True)
    record_a: Mapped[int] = mapped_column(Integer)
    record_b: Mapped[int] = mapped_column(Integer)
    score: Mapped[float] = mapped_column(Float)
    features: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class EntityCluster(Base):
    __tablename__ = "entity_clusters"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"))
    cluster_key: Mapped[str] = mapped_column(String(30))  # ec_00001
    cohesion: Mapped[float] = mapped_column(Float, default=0)
    # pending | confirmed | split
    status: Mapped[str] = mapped_column(String(20), default="pending")
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    members: Mapped[list["ClusterMember"]] = relationship(
        back_populates="cluster", cascade="all, delete-orphan"
    )


class ClusterMember(Base):
    __tablename__ = "cluster_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    cluster_id: Mapped[int] = mapped_column(ForeignKey("entity_clusters.id"))
    record_index: Mapped[int] = mapped_column(Integer)
    record_data: Mapped[dict] = mapped_column(JSON)

    cluster: Mapped[EntityCluster] = relationship(back_populates="members")


class GoldenRecord(Base):
    __tablename__ = "golden_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"))
    cluster_id: Mapped[int] = mapped_column(ForeignKey("entity_clusters.id"), unique=True)
    data: Mapped[dict] = mapped_column(JSON)
    provenance: Mapped[dict] = mapped_column(JSON)
    created_by: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ApiKey(Base):
    """Kunci akses programatik untuk pipeline eksternal (data scientist dkk) menarik
    clean dataset/dictionary/scorecard tanpa login JWT interaktif. Hanya hash yang
    disimpan; kunci lengkap ditampilkan sekali saat dibuat."""
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    name: Mapped[str] = mapped_column(String(200))
    key_prefix: Mapped[str] = mapped_column(String(20))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_by: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class Anomaly(Base):
    __tablename__ = "anomalies"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"))
    column_name: Mapped[str] = mapped_column(String(255))
    record_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    anomaly_type: Mapped[str] = mapped_column(String(50))  # outlier_iqr | outlier_zscore
    value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    explanation: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(20), default="sedang")  # rendah|sedang|tinggi
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class QualityScoreHistory(Base):
    __tablename__ = "quality_score_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"))
    score: Mapped[float] = mapped_column(Float)
    dimensions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    dataset_id: Mapped[int | None] = mapped_column(ForeignKey("datasets.id"), nullable=True)
    alert_type: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20), default="sedang")  # rendah|sedang|tinggi
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CrossDatasetRule(Base):
    """Cek lintas-dataset, dua varian dibedakan lewat check_type:
    - referential_integrity (backlog #10): nilai kolom anak (FK) di primary_dataset yang
      tidak ditemukan di kolom induk (PK) reference_dataset. primary_column/reference_column
      = kolom FK/PK itu sendiri; *_value_column tidak dipakai.
    - consistency (backlog #11): join dua dataset lewat primary_column/reference_column
      sebagai kunci, lalu bandingkan primary_value_column vs reference_value_column untuk
      baris yang cocok — deteksi nilai yang seharusnya sama tapi berbeda antar sumber.
    Dijalankan on-demand (bukan bagian pipeline background); hanya hasil terbaru yang
    disimpan (tanpa tabel histori terpisah)."""
    __tablename__ = "cross_dataset_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    name: Mapped[str] = mapped_column(String(200))
    check_type: Mapped[str] = mapped_column(String(30), default="referential_integrity")
    primary_dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"))
    primary_column: Mapped[str] = mapped_column(String(255))
    reference_dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"))
    reference_column: Mapped[str] = mapped_column(String(255))
    primary_value_column: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reference_value_column: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_checked_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_violations: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_samples: Mapped[list | None] = mapped_column(JSON, nullable=True)


class Pipeline(Base):
    """Konfigurasi pemrosesan granular per dataset (halaman Pipelines): menentukan tahap
    mana dari process_dataset yang benar-benar dijalankan (profiling saja / dedup saja /
    keduanya) dan jadwal eksekusi otomatisnya lewat rq-scheduler (lihat worker/scheduler.py
    schedule_pipeline). Berbeda dari Dataset.monitoring_* (F10) yang selalu menjalankan
    re-validasi penuh — Pipeline sengaja mendukung run parsial."""
    __tablename__ = "pipelines"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"))
    name: Mapped[str] = mapped_column(String(200))
    enable_profiling: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_deduplication: Mapped[bool] = mapped_column(Boolean, default=False)
    # manual | hourly | daily | weekly
    schedule: Mapped[str] = mapped_column(String(20), default="manual")
    schedule_job_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # running | success | failed ("error" tetap dibaca untuk kompatibilitas data lama)
    last_run_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_run_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
