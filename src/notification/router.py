from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sse_starlette import EventSourceResponse
from src.auth.models import Users
from src.auth.dependencies import get_current_user
from src.notification.models import Notification
from src.notification.schema import NotificationRead, NotificationMarkRead
from src.notification.sse_manger import sse_manager
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
import asyncio, json
from uuid import UUID
from src.redis import redis

router = APIRouter()

# SSE stream endpoint
@router.get("/stream")
async def notification_stream(
    request: Request,
    current_user: Users = Depends(get_current_user),
):
    """
    Server-Sent Events endpoint for real-time notifications.
    Frontend should connect to: GET /notification/stream
    """
    # Connect user to SSE manager
    queue = await sse_manager.connect(current_user.id)

    async def event_generator():
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    print(f"Client {current_user.id} disconnected")
                    break
                
                try:
                    # Wait for notification with timeout (heartbeat every 30s)
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {
                        "event": "notification",
                        "data": json.dumps(data),
                    }
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield {
                        "event": "heartbeat",
                        "data": json.dumps({"status": "alive"}),
                    }
        except asyncio.CancelledError:
            print(f"Stream cancelled for user {current_user.id}")
        finally:
            # Clean up when connection closes
            await sse_manager.disconnect(current_user.id)

    return EventSourceResponse(event_generator())


# Get all notifications (polling fallback)
@router.get("")
async def get_notifications(
    current_user: Users = Depends(get_current_user), 
    db: AsyncSession = Depends(get_session),
    limit: int = 50,
    offset: int = 0
) -> list[NotificationRead]:
    """Get user's notifications with pagination"""
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


# Get unread count
@router.get("/unread-count")
async def get_unread_count(
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
) -> dict:
    """Get count of unread notifications"""
    from sqlalchemy import func
    
    result = await db.execute(
        select(func.count(Notification.id))
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        )
    )
    count = result.scalar_one()
    return {"unread_count": count}


# Mark notification as read
@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: UUID,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Mark a specific notification as read"""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        )
    )
    notification = result.scalars().first()
    
    if not notification:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    db.add(notification)
    await db.commit()
    
    return {"message": "Notification marked as read"}


# Mark all notifications as read
@router.post("/mark-all-read")
async def mark_all_read(
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Mark all notifications as read for current user"""
    from sqlalchemy import update
    
    await db.execute(
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        )
        .values(is_read=True)
    )
    await db.commit()
    
    return {"message": "All notifications marked as read"}


# Admin endpoint: Get connection stats
@router.get("/stats")
async def get_notification_stats(
    current_user: Users = Depends(get_current_user),
):
    """Get SSE connection statistics (admin only)"""
    if current_user.role != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin only")
    
    total_connected = await sse_manager.get_connected_users_count()
    
    return {
        "total_connected_users": total_connected,
        "connections_on_this_worker": len(sse_manager.connections)
    }

@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: UUID,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Delete a specific notification"""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        )
    )
    notification = result.scalars().first()
    
    if not notification:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Notification not found")
    
    await db.delete(notification)
    await db.commit()
    cache_key = f"notification_cache:{current_user.id}"
    cached = await redis.lrange(cache_key, 0, -1)

    for notification_json in cached:
        data = json.loads(notification_json)
        if data.get("id") == str(notification_id):
            await redis.lrem(cache_key, 0, notification_json)  # Remove from cache
    
    return {"message": "Notification deleted"}