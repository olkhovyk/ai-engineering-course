from datetime import datetime
from pydantic import BaseModel


class DockBase(BaseModel):
    code: str
    dock_type: str = "standard"


class DockCreate(DockBase):
    pass


class DockStatusUpdate(BaseModel):
    status: str


class DockOut(DockBase):
    id: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
