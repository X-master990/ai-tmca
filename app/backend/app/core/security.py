"""密碼雜湊 + JWT — Phase 1 會用到，先放骨架"""
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(payload: dict, ttl_hours: int | None = None) -> str:
    ttl = ttl_hours if ttl_hours is not None else settings.jwt_ttl_hours
    expire = datetime.now(tz=timezone.utc) + timedelta(hours=ttl)
    data = {**payload, "exp": expire}
    return jwt.encode(data, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
