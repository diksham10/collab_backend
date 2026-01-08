from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from uuid import UUID, uuid4
from src.myenums import SocialPlatform

if TYPE_CHECKING:
    from auth.models import Users
    from event.models import EventApplication

class InfluencerProfile(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    name: str
    niche: Optional[str] = None
    audience_size: Optional[int] = None
    engagement_rate: Optional[float] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # Relationships using forward references
    user: "Users" = Relationship(back_populates="influencer_profile")
    social_links: List["SocialLink"] = Relationship(back_populates="influencer_profile")
    applications: List["EventApplication"] = Relationship(back_populates="influencer")


class SocialLink(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    influencer_profile_id: UUID = Field(foreign_key="influencerprofile.id")
    platform: SocialPlatform
    url: str
    followers: Optional[int] = None
    linked_at: Optional[str] = None

    # Relationship using forward reference
    influencer_profile: "InfluencerProfile" = Relationship(back_populates="social_links")


# Resolve forward references at the end
from src.auth.models import Users
from src.event.models import EventApplication

InfluencerProfile.update_forward_refs()
SocialLink.update_forward_refs()
