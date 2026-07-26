"""Koneksi database langsung (backlog #2): tarik data dari PostgreSQL/MySQL sebagai
sumber dataset alternatif selain upload file. Kredensial dienkripsi at-rest (Fernet) —
tanpa ENCRYPTION_KEY dikonfigurasi, fitur ini nonaktif secara graceful (pola yang sama
dengan services/llm.py).
"""
from __future__ import annotations

from urllib.parse import quote_plus

import pandas as pd
from cryptography.fernet import Fernet
from sqlalchemy import create_engine, text

from ..config import settings

DB_TYPES = {"postgresql": "postgresql+psycopg2", "mysql": "mysql+pymysql"}


def encryption_available() -> bool:
    return bool(settings.encryption_key)


def _fernet() -> Fernet:
    if not encryption_available():
        raise RuntimeError(
            "Koneksi database belum bisa dipakai — set ENCRYPTION_KEY di .env. Generate "
            'dengan: python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"'
        )
    return Fernet(settings.encryption_key.encode())


def encrypt_password(raw: str) -> str:
    return _fernet().encrypt(raw.encode()).decode()


def decrypt_password(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()


def build_url(db_type: str, host: str, port: int, database: str, username: str,
             password: str) -> str:
    driver = DB_TYPES.get(db_type)
    if driver is None:
        raise ValueError(f"Tipe database tidak didukung: {db_type}")
    return (f"{driver}://{quote_plus(username)}:{quote_plus(password)}"
            f"@{host}:{port}/{database}")


def test_connection(db_type: str, host: str, port: int, database: str, username: str,
                    password: str) -> None:
    """Lempar exception dengan pesan jelas bila koneksi/kredensial salah."""
    engine = create_engine(build_url(db_type, host, port, database, username, password),
                           connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    finally:
        engine.dispose()


def fetch_dataframe(db_type: str, host: str, port: int, database: str, username: str,
                    password: str, query: str) -> pd.DataFrame:
    engine = create_engine(build_url(db_type, host, port, database, username, password),
                           connect_args={"connect_timeout": 10})
    try:
        df = pd.read_sql(text(query), engine)
    finally:
        engine.dispose()
    if df.empty:
        raise ValueError("Query tidak mengembalikan baris data")
    return df
