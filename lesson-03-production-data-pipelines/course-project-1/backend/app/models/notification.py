from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Integer, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(10), default="info")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    source_agent: Mapped[str] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
