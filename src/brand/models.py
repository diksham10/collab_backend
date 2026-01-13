from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from uuid import uuid4, UUID

if TYPE_CHECKING:
    from auth.models import Users
    from event.models import Event

class BrandProfile(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False)
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    website_url: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # Relationships using forward references
    user: "Users" = Relationship(back_populates="brand_profile")
    events: List["Event"] = Relationship(back_populates="brand")


# Resolve forward references after all models are imported
from src.auth.models import Users
from src.event.models import Event

BrandProfile.update_forward_refs()
