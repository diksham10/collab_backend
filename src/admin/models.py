from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship, Column, ForeignKey
from src.myenums import UserRole
from uuid import UUID, uuid4
from sqlalchemy.orm import Mapped

if TYPE_CHECKING:
    from src.auth.models import Users

class Admin(SQLModel, table=True):
    __tablename__ = "admin"
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False))
    role: UserRole 
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship
    user: Mapped["Users"] = Relationship(back_populates="admin")

from src.auth.models import Users
Admin.update_forward_refs()
