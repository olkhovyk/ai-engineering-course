from datetime import datetime, date, time, timezone

from sqlalchemy import String, DateTime, Integer, Date, Time, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Shift(Base):
    __tablename__ = "shifts"
    __table_args__ = (
        UniqueConstraint("staff_id", "shift_date", "start_time", name="uq_shift_staff_date_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff.id"), nullable=False)
    shift_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    created_by: Mapped[str] = mapped_column(String(50), default="manual")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
