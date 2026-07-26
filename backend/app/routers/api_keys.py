from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ApiKey, User
from ..security import generate_api_key, get_current_user, require_writer

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class ApiKeyCreate(BaseModel):
    name: str


def _key_dict(key: ApiKey) -> dict:
    return {
        "id": key.id,
        "name": key.name,
        "key_prefix": key.key_prefix,
        "created_by": key.created_by,
        "created_at": key.created_at.isoformat(),
        "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
        "revoked": key.revoked,
    }


@router.get("")
def list_api_keys(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    keys = (db.query(ApiKey).filter_by(org_id=user.org_id)
            .order_by(desc(ApiKey.created_at)).all())
    return [_key_dict(k) for k in keys]


@router.post("")
def create_api_key(body: ApiKeyCreate, db: Session = Depends(get_db),
                   user: User = Depends(require_writer)):
    if not body.name.strip():
        raise HTTPException(400, "Nama API key tidak boleh kosong")
    raw_key, prefix, key_hash = generate_api_key()
    key = ApiKey(org_id=user.org_id, name=body.name.strip(), key_prefix=prefix,
                key_hash=key_hash, created_by=user.email)
    db.add(key)
    db.commit()
    out = _key_dict(key)
    out["key"] = raw_key  # hanya muncul di respons ini, tidak pernah lagi setelahnya
    return out


@router.delete("/{key_id}")
def revoke_api_key(key_id: int, db: Session = Depends(get_db),
                   user: User = Depends(require_writer)):
    key = db.get(ApiKey, key_id)
    if key is None or key.org_id != user.org_id:
        raise HTTPException(404, "API key tidak ditemukan")
    key.revoked = True
    db.commit()
    return {"revoked": True}
