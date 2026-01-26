from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sse_starlette import EventSourceResponse
from src.auth.models import Users
from src.auth.dependencies import get_current_user
from src.notification.models import Notification
from src.notification.schema import NotificationRead
from src.notification.sse_manger import NotificationSSEManager
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
import asyncio, json
from uuid import UUID

router = APIRouter()

sse_manager = NotificationSSEManager()
# SSE stream
@router.get("/notifications/stream")
async def notification_stream(
    request: Request,
    current_user: Users = Depends(get_current_user),
):
    queue = await sse_manager.connect(current_user.id)

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            data = await queue.get()
            yield {
                "event": "notification",
                "data": json.dumps(data),
            }

    return EventSourceResponse(event_generator())

# Polling endpoint 
@router.get("/notifications")
async def get_notifications(current_user:Users = Depends(get_current_user), db: AsyncSession = Depends(get_session)) -> list[NotificationRead]:
    result = await db.execute(
        select(Notification).where(Notification.user_id == current_user.id).order_by(Notification.created_at.desc())
    )
    return result.scalars().all()
