import logging
import os
from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
logger = logging.getLogger("suricatajs")


def require_api_key(api_key: str = Security(_api_key_header)) -> str:
    configured = {k for k in os.getenv("API_KEYS", "").split(",") if k}
    if not configured:
        logger.error("API_KEYS environment variable is not set — all requests are being rejected")
        raise HTTPException(status_code=401, detail="Unauthorized")
    if api_key not in configured:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return api_key
