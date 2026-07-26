from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://dataklin:dataklin@localhost:5432/dataklin"
    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "dataklin-raw"

    jwt_secret: str = "change-me-in-production"
    jwt_expire_minutes: int = 720

    admin_email: str = "admin@dataklin.local"
    admin_password: str = "admin123"
    admin_name: str = "Admin Dataklin"

    default_alert_threshold: int = 75
    cors_origins: str = "http://localhost:3000"

    # LLM gateway (OpenAI-compatible). Kosong = fitur AI nonaktif (lihat docs/ENHANCEMENTS.md)
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    # SMTP untuk notifikasi email (F10/F12). smtp_host kosong = email nonaktif graceful.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "dataklin@localhost"
    smtp_use_tls: bool = True

    # Enkripsi kredensial koneksi database (backlog #2). Kosong = fitur nonaktif graceful.
    # Generate dengan: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    encryption_key: str = ""

    max_upload_mb: int = 200
    er_max_rows: int = 200_000
    er_pair_threshold: float = 0.8
    er_max_block_size: int = 60
    er_max_pairs: int = 200_000

    class Config:
        env_file = ".env"


settings = Settings()
