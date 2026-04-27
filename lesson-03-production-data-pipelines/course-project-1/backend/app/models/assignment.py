from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    schedule_entry_id: Mapped[int] = mapped_column(ForeignKey("delivery_schedule.id"), nullable=False)
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff.id"), nullable=False)
    dock_id: Mapped[int] = mapped_column(ForeignKey("docks.id"), nullable=False)
    role_needed: Mapped[str] = mapped_column(String(30), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_by: Mapped[str] = mapped_column(String(50), default="manual")
