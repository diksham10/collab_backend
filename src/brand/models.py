from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column, ForeignKey
from uuid import uuid4, UUID
from sqlalchemy.orm import Mapped

if TYPE_CHECKING:
    from auth.models import Users
    from event.models import Event

class BrandProfile(SQLModel, table=True):
    __tablename__ = "brandprofile"
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        sa_column=Column(
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False
        )
)   
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    website_url: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # Relationships using forward references
    user: Mapped["Users"] = Relationship(back_populates="brands")
    events: Mapped[List["Event"]] = Relationship(back_populates="brand", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


# Resolve forward references after all models are imported
from src.auth.models import Users
from src.event.models import Event

BrandProfile.update_forward_refs()
