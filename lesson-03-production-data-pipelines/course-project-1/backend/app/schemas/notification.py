from datetime import datetime
from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: int
    title: str
    body: str
    severity: str
    is_read: bool
    source_agent: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
