import datetime
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import text

from api.auth import (
    create_token,
    get_current_user,
    hash_password,
    verify_password,
)
from api.models import LoginRequest, PatchMeRequest, UserResponse
from db.database import get_connection

logger = logging.getLogger("suricatajs")
router = APIRouter(prefix="/auth")


def _get_user_by_id(user_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            text("SELECT id, email, name, role, created_at FROM users WHERE id = :id"),
            {"id": user_id},
        ).fetchone()
    if not row:
        return None
    return {"id": row[0], "email": row[1], "name": row[2], "role": row[3], "created_at": row[4]}


@router.post("/login", response_model=UserResponse)
def login(body: LoginRequest, response: Response):
    with get_connection() as conn:
        row = conn.execute(
            text("SELECT id, email, name, role, created_at, password_hash FROM users WHERE email = :email"),
            {"email": body.email},
        ).fetchone()
    if not row or not verify_password(body.password, row[5]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(row[0], row[3])
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return UserResponse(id=row[0], email=row[1], name=row[2], role=row[3], created_at=row[4])


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="session", path="/")
    return {"ok": True}


@router.get("/me", response_model=UserResponse)
def me(current_user: dict = Depends(get_current_user)):
    user = _get_user_by_id(current_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(**user)


@router.patch("/me", response_model=UserResponse)
def patch_me(body: PatchMeRequest, current_user: dict = Depends(get_current_user)):
    updates, params = [], {"id": current_user["id"]}
    if body.name is not None:
        updates.append("name = :name")
        params["name"] = body.name
    if body.password is not None:
        if len(body.password) < 8:
            raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
        updates.append("password_hash = :hash")
        params["hash"] = hash_password(body.password)
    if not updates:
        raise HTTPException(status_code=422, detail="Nothing to update")
    with get_connection() as conn:
        if "name" in params and "hash" in params:
            sql = "UPDATE users SET name = :name, password_hash = :hash WHERE id = :id"
        elif "name" in params:
            sql = "UPDATE users SET name = :name WHERE id = :id"
        else:
            sql = "UPDATE users SET password_hash = :hash WHERE id = :id"
        conn.execute(text(sql), params)
    user = _get_user_by_id(current_user["id"])
    return UserResponse(**user)
