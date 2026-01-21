from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column, ForeignKey
from uuid import UUID, uuid4
from src.myenums import SocialPlatform
from sqlalchemy.orm import Mapped

if TYPE_CHECKING:
    from auth.models import Users
    from event.models import EventApplication

class InfluencerProfile(SQLModel, table=True):
    __tablename__ = "influencerprofile"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True))
    name: str
    niche: Optional[str] = None
    audience_size: Optional[int] = None
    engagement_rate: Optional[float] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # Relationships using forward references
    user: Mapped["Users"] = Relationship(back_populates="influencer_profile")
    social_links: Mapped[List["SocialLink"]] = Relationship(back_populates="influencer_profile", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    applications: Mapped[List["EventApplication"]] = Relationship(back_populates="influencer", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class SocialLink(SQLModel, table=True):
    __tablename__ = "sociallink"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    influencer_profile_id: UUID = Field(sa_column=Column(ForeignKey("influencerprofile.id", ondelete="CASCADE"), nullable=False))   #social link id =influencer profile id
    platform: SocialPlatform
    url: str
    followers: Optional[int] = None
    linked_at: Optional[str] = None

    # Relationship using forward reference
    influencer_profile: Mapped["InfluencerProfile"] = Relationship(back_populates="social_links")


# Resolve forward references at the end
from src.auth.models import Users
from src.event.models import EventApplication

InfluencerProfile.update_forward_refs()
SocialLink.update_forward_refs()
