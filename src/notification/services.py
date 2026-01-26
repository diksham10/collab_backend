from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from src.notification.models import Notification
from src.myenums import NotificationType
from src.notification.templates import NOTIFICATION_TEMPLATES
from src.notification.sse_manger import NotificationSSEManager

async def create_notification(
    db: AsyncSession,
    user_id: UUID,
    type: NotificationType,
    context: dict,
    data: dict | None = None,
) -> Notification:
    # get template
    template = NOTIFICATION_TEMPLATES[type]
    if isinstance(template, dict) and "status" in context:
        template = template[context["status"]]

    title = template["title"]
    message = template["message"].format(**context)

    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        data=data,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)


    #puuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuush to sse manager
    await NotificationSSEManager().push(user_id, {
        "id": str(notification.id),
        "type": notification.type.value,
        "title": notification.title,
        "message": notification.message,
        "data": notification.data,
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat(),
    })

    return notification
