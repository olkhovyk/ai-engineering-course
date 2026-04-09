from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


async def get_notifications(db: AsyncSession, limit: int = 50) -> list[Notification]:
    q = select(Notification).order_by(Notification.is_read, Notification.created_at.desc()).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_unread_count(db: AsyncSession) -> int:
    q = select(func.count()).select_from(Notification).where(Notification.is_read == False)
    result = await db.execute(q)
    return result.scalar() or 0


async def mark_read(db: AsyncSession, notification_id: int) -> bool:
    n = await db.get(Notification, notification_id)
    if not n:
        return False
    n.is_read = True
    await db.commit()
    return True


async def mark_all_read(db: AsyncSession) -> int:
    stmt = update(Notification).where(Notification.is_read == False).values(is_read=True)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount


async def create_notification(db: AsyncSession, title: str, body: str, severity: str = "info", source_agent: str | None = None) -> Notification:
    n = Notification(title=title, body=body, severity=severity, source_agent=source_agent)
    db.add(n)
    await db.commit()
    await db.refresh(n)
    return n
