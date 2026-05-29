import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Cookie, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
logger = logging.getLogger("suricatajs")

_jwt_secret: Optional[str] = None


def get_jwt_secret() -> str:
    global _jwt_secret
    if _jwt_secret:
        return _jwt_secret
    env_secret = os.getenv("JWT_SECRET")
    if env_secret:
        _jwt_secret = env_secret
    else:
        _jwt_secret = secrets.token_hex(32)
        logger.warning("JWT_SECRET not set — generating ephemeral secret. "
                       "Sessions will be invalidated on restart.")
    return _jwt_secret


def create_token(user_id: int, role: str) -> str:
    expire_minutes = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    payload = {"sub": str(user_id), "role": role, "exp": expire}
    return jwt.encode(payload, get_jwt_secret(), algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, get_jwt_secret(), algorithms=["HS256"])


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def get_current_user(session: Optional[str] = Cookie(default=None)) -> dict:
    """JWT-cookie-only dependency. Returns {id, role}. Raises 401 if missing/invalid."""
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(session)
        return {"id": int(payload["sub"]), "role": payload["role"]}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired session")


def require_admin(session: Optional[str] = Cookie(default=None)) -> dict:
    user = get_current_user(session)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def require_api_key(api_key: str = Security(_api_key_header)) -> str:
    """Kept for backwards compatibility with existing scanner/API clients."""
    configured = {k for k in os.getenv("API_KEYS", "").split(",") if k}
    if not configured:
        logger.error("API_KEYS environment variable is not set — all requests are being rejected")
        raise HTTPException(status_code=401, detail="Unauthorized")
    if api_key not in configured:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return api_key


def require_any_auth(
    api_key: str = Security(_api_key_header),
    session: Optional[str] = Cookie(default=None),
) -> None:
    """Accepts either a valid JWT cookie or a valid X-API-Key header."""
    if session:
        try:
            decode_token(session)
            return
        except jwt.PyJWTError:
            pass
    configured = {k for k in os.getenv("API_KEYS", "").split(",") if k}
    if configured and api_key in configured:
        return
    if not configured:
        logger.error("API_KEYS environment variable is not set — all requests are being rejected")
    raise HTTPException(status_code=401, detail="Unauthorized")
