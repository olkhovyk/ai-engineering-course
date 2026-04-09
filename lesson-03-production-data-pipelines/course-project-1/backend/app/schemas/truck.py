from datetime import datetime
from pydantic import BaseModel


class TruckBase(BaseModel):
    license_plate: str
    carrier_name: str
    cargo_type: str = "palletized"
    cargo_volume_pallets: int = 0


class TruckCreate(TruckBase):
    pass


class TruckUpdate(BaseModel):
    status: str | None = None
    cargo_volume_pallets: int | None = None


class TruckOut(TruckBase):
    id: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
