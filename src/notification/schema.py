from pydantic import BaseModel
from typing import List, Optional 
from uuid import UUID
from src.myenums import NotificationType


class NotificationRead(BaseModel):
    id: Optional[UUID]
    type:NotificationType
    title: Optional[str] = None
    message: Optional[str] = None
    metadata: Optional[dict]= None
    is_read: Optional[bool] = False
    created_at: Optional[str] = None