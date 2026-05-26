from pydantic import BaseModel
from typing import Optional


class AlertResponse(BaseModel):
    javascript: str
    stored_checksum: Optional[str] = None
    new_checksum: Optional[str] = None
    date: str
    alert_msg: str
    alert_type: str
