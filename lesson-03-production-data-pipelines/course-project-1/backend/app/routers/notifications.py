from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.notification import NotificationOut
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
async def list_notifications(limit: int = 50, db: AsyncSession = Depends(get_db)):
    return await notification_service.get_notifications(db, limit)


@router.patch("/{notification_id}/read")
async def mark_read(notification_id: int, db: AsyncSession = Depends(get_db)):
    if not await notification_service.mark_read(db, notification_id):
        raise HTTPException(404, "Notification not found")
    return {"ok": True}


@router.patch("/read-all")
async def mark_all_read(db: AsyncSession = Depends(get_db)):
    count = await notification_service.mark_all_read(db)
    return {"marked": count}
