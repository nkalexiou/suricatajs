import datetime
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import text

from api.auth import hash_password, require_admin
from api.models import UserCreate, UserResponse
from db.database import get_connection

logger = logging.getLogger("suricatajs")
router = APIRouter(prefix="/users")


@router.get("", response_model=List[UserResponse])
def list_users(current_user: dict = Depends(require_admin)):
    with get_connection() as conn:
        rows = conn.execute(
            text("SELECT id, email, name, role, created_at FROM users ORDER BY created_at")
        ).fetchall()
    return [UserResponse(id=r[0], email=r[1], name=r[2], role=r[3], created_at=r[4]) for r in rows]


@router.post("", response_model=UserResponse, status_code=201)
def create_user(body: UserCreate, current_user: dict = Depends(require_admin)):
    if body.role not in ("admin", "operator"):
        raise HTTPException(status_code=422, detail="role must be 'admin' or 'operator'")
    if len(body.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    try:
        with get_connection() as conn:
            result = conn.execute(
                text("INSERT INTO users (email, name, password_hash, role, created_at) "
                     "VALUES (:email, :name, :hash, :role, :now)"),
                {"email": body.email, "name": body.name,
                 "hash": hash_password(body.password), "role": body.role, "now": now},
            )
            new_id = result.lastrowid
            row = conn.execute(
                text("SELECT id, email, name, role, created_at FROM users WHERE id = :id"),
                {"id": new_id},
            ).fetchone()
    except Exception as e:
        if "UNIQUE" in str(e) or "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail="Email already exists")
        raise
    return UserResponse(id=row[0], email=row[1], name=row[2], role=row[3], created_at=row[4])


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, current_user: dict = Depends(require_admin)):
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    with get_connection() as conn:
        result = conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")
    return Response(status_code=204)
