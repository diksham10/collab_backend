from typing import Optional,TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship, Column, ForeignKey
from uuid import uuid4, UUID
from sqlalchemy.orm import Mapped

class AdminLog(SQLModel, table=True):
    __tablename__ = "adminlog"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    admin_id: UUID = Field(sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False))
    action_type: str
    target_id: Optional[UUID] = None
    details: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship
    admin: Mapped["Users"] = Relationship(back_populates="admin_logs")

from src.auth.models import Users
AdminLog.update_forward_refs()