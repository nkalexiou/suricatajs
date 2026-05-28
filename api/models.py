from pydantic import BaseModel
from typing import List, Optional


class AlertResponse(BaseModel):
    id: int
    javascript: str
    stored_checksum: Optional[str] = None
    new_checksum: Optional[str] = None
    date: str
    alert_msg: str
    alert_type: str
    diff: Optional[str] = None
    sri: Optional[str] = None


class DiffResponse(BaseModel):
    alert_id: int
    diff: str


class TargetCreate(BaseModel):
    url: str
    name: Optional[str] = None
    tags: Optional[List[str]] = None
    owner: Optional[str] = None
    scan_interval_minutes: Optional[int] = None
    crawl_depth: Optional[int] = 0
    use_playwright: Optional[bool] = False


class TargetResponse(BaseModel):
    id: int
    url: str
    name: Optional[str] = None
    tags: Optional[List[str]] = None
    owner: Optional[str] = None
    scan_interval_minutes: Optional[int] = None
    approved_checksum: Optional[str] = None
    approval_note: Optional[str] = None
    approved_at: Optional[str] = None
    created_at: str
    crawl_depth: int = 0
    use_playwright: bool = False


class ApproveRequest(BaseModel):
    note: Optional[str] = None
