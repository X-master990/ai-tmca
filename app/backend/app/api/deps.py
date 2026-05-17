"""FastAPI 依賴：解 JWT、取得目前 user、角色守門。"""
from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.database import get_db
from app.models import User

COOKIE_NAME = "tmca_token"


def _extract_token(authorization: str | None, cookie_token: str | None) -> str | None:
    """同時支援 Authorization: Bearer 與 HttpOnly Cookie。Header 優先。"""
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
    return cookie_token


def get_current_user(
    authorization: str | None = Header(default=None),
    tmca_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User:
    token = _extract_token(authorization, tmca_token)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "未提供認證資訊")

    payload = decode_token(token)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token 無效或已過期")

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token 缺少 sub")

    user = db.query(User).filter(User.username == sub).first()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "使用者不存在或已停用")

    return user


def require_role(*allowed: str):
    """工廠：產生「限定角色」的依賴。
    例：`Depends(require_role('officer_a', 'officer_b'))`
    """
    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "權限不足")
        return user
    return _checker
