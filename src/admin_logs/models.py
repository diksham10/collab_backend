from typing import Optional,TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from uuid import uuid4, UUID

class AdminLog(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    admin_id: UUID = Field(foreign_key="users.id", nullable=False)
    action_type: str
    target_id: Optional[UUID] = None
    details: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship
    admin: "Users" = Relationship(back_populates="admin_logs")

from src.auth.models import Users
AdminLog.update_forward_refs()