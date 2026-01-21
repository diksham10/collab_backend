from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship, Column,ForeignKey
from uuid import UUID, uuid4
from src.myenums import ApplicationStatus
from sqlalchemy.orm import Mapped

if TYPE_CHECKING:
    from auth.models import Users  
    from influencer.models import InfluencerProfile
    from brand.models import BrandProfile

class Event(SQLModel, table=True):
    __tablename__ = "event"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(sa_column=Column(ForeignKey("users.id", ondelete="CASCADE")))
    brand_id: UUID = Field(sa_column=Column(ForeignKey("brandprofile.id", ondelete="CASCADE")))
    title: str
    description: Optional[str] = None
    objectives: Optional[str] = None
    budget: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    deliverables: Optional[str] = None
    target_audience: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    status: str = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships with forward references
    brand: Mapped["BrandProfile"] = Relationship(back_populates="events")
    applications: Mapped[List["EventApplication"]] = Relationship(back_populates="event", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    ratings: Mapped[List["Rating"]] = Relationship(back_populates="event", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class EventApplication(SQLModel, table=True):
    __tablename__ = "eventapplication"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    event_id: UUID = Field(sa_column=Column(ForeignKey("event.id", ondelete="CASCADE")))
    influencer_id: UUID = Field(sa_column=Column(ForeignKey("influencerprofile.id", ondelete="CASCADE")))
    status: ApplicationStatus = ApplicationStatus.pending
    applied_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    event: Mapped["Event"] = Relationship(back_populates="applications")
    influencer: Mapped["InfluencerProfile"] = Relationship(back_populates="applications")
    messages: Mapped[List["Message"]] = Relationship(back_populates="application", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    

# Resolve forward references
from src.auth.models import Users  
from src.influencer.models import InfluencerProfile
from src.brand.models import BrandProfile
from src.chat.models import Message
from src.ratings.models import Rating
Event.update_forward_refs()
EventApplication.update_forward_refs()
