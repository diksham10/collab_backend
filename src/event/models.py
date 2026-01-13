from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from uuid import UUID, uuid4
from src.myenums import ApplicationStatus

if TYPE_CHECKING:
    from auth.models import Users  
    from influencer.models import InfluencerProfile
    from brand.models import BrandProfile

class Event(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    brand_id: UUID = Field(foreign_key="brandprofile.id")
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
    brand: "BrandProfile" = Relationship(back_populates="events")
    applications: List["EventApplication"] = Relationship(back_populates="event")
    ratings: List["Rating"] = Relationship(back_populates="event")

class EventApplication(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    event_id: UUID = Field(foreign_key="event.id")
    influencer_id: UUID = Field(foreign_key="influencerprofile.id")
    status: ApplicationStatus = ApplicationStatus.pending
    applied_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    event: "Event" = Relationship(back_populates="applications")
    influencer: "InfluencerProfile" = Relationship(back_populates="applications")
    messages: List["Message"] = Relationship(back_populates="application")
    

# Resolve forward references
from src.auth.models import Users  
from src.influencer.models import InfluencerProfile
from src.brand.models import BrandProfile
from src.chat.models import Message
from src.ratings.models import Rating
Event.update_forward_refs()
EventApplication.update_forward_refs()
