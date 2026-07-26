from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import DataConnection, Dataset, User
from ..security import get_current_user, require_writer
from ..services.db_connector import DB_TYPES, encrypt_password, encryption_available, test_connection

router = APIRouter(prefix="/connections", tags=["connections"])


class ConnectionCreate(BaseModel):
    name: str
    db_type: str
    host: str
    port: int
    database: str
    username: str
    password: str


def _dict(c: DataConnection) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "db_type": c.db_type,
        "host": c.host,
        "port": c.port,
        "database": c.database,
        "username": c.username,
        "created_by": c.created_by,
        "created_at": c.created_at.isoformat(),
    }


@router.get("/available")
def connections_available():
    return {"available": encryption_available(), "db_types": list(DB_TYPES)}


@router.get("")
def list_connections(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conns = db.query(DataConnection).filter_by(org_id=user.org_id).order_by(
        DataConnection.created_at.desc()).all()
    return [_dict(c) for c in conns]


@router.post("")
def create_connection(body: ConnectionCreate, db: Session = Depends(get_db),
                      user: User = Depends(require_writer)):
    if not encryption_available():
        raise HTTPException(503, "Koneksi database belum dikonfigurasi — set ENCRYPTION_KEY di .env")
    if body.db_type not in DB_TYPES:
        raise HTTPException(400, f"db_type harus salah satu dari: {', '.join(DB_TYPES)}")
    try:
        test_connection(body.db_type, body.host, body.port, body.database,
                        body.username, body.password)
    except Exception as exc:  # noqa: BLE001 - error driver DB beragam, tampilkan apa adanya
        raise HTTPException(400, f"Gagal terhubung ke database: {exc}")

    conn = DataConnection(
        org_id=user.org_id, name=body.name, db_type=body.db_type, host=body.host,
        port=body.port, database=body.database, username=body.username,
        password_encrypted=encrypt_password(body.password), created_by=user.email,
    )
    db.add(conn)
    db.commit()
    return _dict(conn)


@router.delete("/{connection_id}")
def delete_connection(connection_id: int, db: Session = Depends(get_db),
                      user: User = Depends(require_writer)):
    conn = db.get(DataConnection, connection_id)
    if conn is None or conn.org_id != user.org_id:
        raise HTTPException(404, "Koneksi tidak ditemukan")
    in_use = db.query(Dataset).filter_by(connection_id=connection_id).count()
    if in_use:
        raise HTTPException(409, f"Koneksi masih dipakai {in_use} dataset — hapus dataset "
                                 "itu dulu sebelum menghapus koneksi")
    db.delete(conn)
    db.commit()
    return {"deleted": True}
