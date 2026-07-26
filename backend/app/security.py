import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import ApiKey, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)
API_KEY_HEADER = "X-API-Key"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "exp": datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token tidak ditemukan")
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token tidak valid")
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Pengguna tidak ditemukan")
    return user


def require_writer(user: User = Depends(get_current_user)) -> User:
    if user.role not in ("admin", "analyst"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Role viewer tidak boleh mengubah data")
    return user


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Kembalikan (kunci_lengkap, prefix_tampilan, hash_tersimpan). Kunci lengkap hanya
    ditampilkan sekali saat dibuat — server hanya menyimpan hash-nya."""
    raw_key = f"vd_{secrets.token_urlsafe(32)}"
    return raw_key, raw_key[:12], hash_api_key(raw_key)


@dataclass
class Actor:
    """Identitas pemanggil API untuk endpoint konsumsi data — bisa user (JWT) atau
    pipeline eksternal (API key). Dipakai di endpoint read-only/export, bukan di endpoint
    yang mengubah data (mutasi tetap butuh JWT agar audit trail mencatat nama pengguna)."""
    org_id: int
    label: str


def get_org_reader(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Actor:
    api_key = request.headers.get(API_KEY_HEADER)
    if api_key:
        record = db.query(ApiKey).filter_by(
            key_hash=hash_api_key(api_key), revoked=False).first()
        if record is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "API key tidak valid atau dicabut")
        record.last_used_at = datetime.utcnow()
        db.commit()
        return Actor(org_id=record.org_id, label=f"api_key:{record.name}")
    user = get_current_user(credentials, db)
    return Actor(org_id=user.org_id, label=user.email)
