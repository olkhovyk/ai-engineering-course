from datetime import datetime
from pydantic import BaseModel


class AgentLogOut(BaseModel):
    id: int
    agent_name: str
    event_type: str
    severity: str
    message: str
    payload: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}
