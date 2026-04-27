from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Truck(Base):
    __tablename__ = "trucks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    license_plate: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    carrier_name: Mapped[str] = mapped_column(String(100), nullable=False)
    cargo_type: Mapped[str] = mapped_column(String(50), default="palletized")
    cargo_volume_pallets: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
