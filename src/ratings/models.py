from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship, Column, ForeignKey
from uuid import UUID, uuid4
from sqlalchemy.orm import Mapped

if TYPE_CHECKING:
    from auth.models import Users  # type hint only
    from event.models import Event  # type hint only

class Rating(SQLModel, table=True):
    __tablename__ = "rating"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    rater_id: UUID = Field(sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False))
    ratee_id: UUID = Field(sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False))
    event_id: Optional[UUID] = Field(default=None, sa_column=Column(ForeignKey("event.id", ondelete="CASCADE"), nullable=True))
    score: Optional[float] = None
    review: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships using forward references
    rater: Mapped["Users"] = Relationship(
        back_populates="ratings_given",
        sa_relationship_kwargs={"foreign_keys": "[Rating.rater_id]"}
    )
    ratee: Mapped["Users"] = Relationship(
        back_populates="ratings_received",
        sa_relationship_kwargs={"foreign_keys": "[Rating.ratee_id]"}
    )
    event: Mapped[Optional["Event"]] = Relationship(back_populates="ratings")

# Resolve forward references at the end
from src.auth.models import Users
from src.event.models import Event

Rating.update_forward_refs()
