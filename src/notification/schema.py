from pydantic import BaseModel
from typing import List, Optional 
from uuid import UUID
from datetime import datetime
from src.myenums import NotificationType


class NotificationRead(BaseModel):
    id: Optional[UUID]
    type:NotificationType
    title: Optional[str] = None
    message: Optional[str] = None
    data: Optional[dict]= None
    is_read: Optional[bool] = False
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class NotificationMarkRead(BaseModel):
    """Schema for marking notifications as read"""
    is_read: bool = True


class NotificationCreate(BaseModel):
    """Schema for creating notifications (internal use)"""
    user_id: UUID
    type: NotificationType
    title: Optional[str] = None
    message: str
    data: Optional[dict] = None