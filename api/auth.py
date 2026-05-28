import os
from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str = Security(_api_key_header)) -> str:
    configured = {k for k in os.getenv("API_KEYS", "").split(",") if k}
    if not configured:
        raise HTTPException(status_code=401, detail="API_KEYS not configured — set the API_KEYS environment variable")
    if api_key not in configured:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return api_key
