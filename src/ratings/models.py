from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from auth.models import Users  # type hint only
    from event.models import Event  # type hint only

class Rating(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    rater_id: UUID = Field(foreign_key="users.id")
    ratee_id: UUID = Field(foreign_key="users.id")
    event_id: Optional[UUID] = Field(default=None, foreign_key="event.id")
    score: Optional[float] = None
    review: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships using forward references
    rater: "Users" = Relationship(
        back_populates="ratings_given",
        sa_relationship_kwargs={"foreign_keys": "[Rating.rater_id]"}
    )
    ratee: "Users" = Relationship(
        back_populates="ratings_received",
        sa_relationship_kwargs={"foreign_keys": "[Rating.ratee_id]"}
    )
    event: Optional["Event"] = Relationship(back_populates="ratings")

# Resolve forward references at the end
from src.auth.models import Users
from src.event.models import Event

Rating.update_forward_refs()
