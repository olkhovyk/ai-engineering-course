from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class DeliverySchedule(Base):
    __tablename__ = "delivery_schedule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    truck_id: Mapped[int] = mapped_column(ForeignKey("trucks.id"), nullable=False)
    expected_arrival: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual_arrival: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    dock_id: Mapped[Optional[int]] = mapped_column(ForeignKey("docks.id"), nullable=True)
    estimated_unload_minutes: Mapped[int] = mapped_column(Integer, default=60)
    status: Mapped[str] = mapped_column(String(20), default="planned")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
