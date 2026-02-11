from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from src.myenums import UserRole
from uuid import UUID, uuid4
from sqlalchemy.orm import Mapped

if TYPE_CHECKING:
    from src.brand.models import BrandProfile
    from influencer.models import InfluencerProfile
    from event.models import Event, EventApplication
    from chat.models import Message
    from notification.models import Notification
    from ratings.models import Rating
    from admin_logs.models import AdminLog
    from otp.models import OtpModel
    from src.admin.models import Admin
    

class Users(SQLModel, table=True):
    __tablename__ = "users" 

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True, index=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    role: UserRole
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    
    brands: Mapped[List["BrandProfile"]] = Relationship(back_populates="user",sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    influencer_profile: Optional["InfluencerProfile"] = Relationship(back_populates="user",sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    admin: Optional["Admin"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    # events: List["Event"] = Relationship(back_populates="brand")
    # applications: List["EventApplication"] = Relationship(back_populates="influencer")
    sent_messages: Mapped[List["Message"]] = Relationship(
        back_populates="sender",
        sa_relationship_kwargs={"foreign_keys": "[Message.sender_id]", "cascade": "all, delete-orphan"}
    )
    received_messages: Mapped[List["Message"]] = Relationship(
        back_populates="receiver",
        sa_relationship_kwargs={"foreign_keys": "[Message.receiver_id]", "cascade": "all, delete-orphan"}
    )
    notifications: Mapped[List["Notification"]] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    ratings_given: Mapped[List["Rating"]] = Relationship(
        back_populates="rater",
        sa_relationship_kwargs={"foreign_keys": "[Rating.rater_id]", "cascade": "all, delete-orphan"}
    )
    ratings_received: Mapped[List["Rating"]] = Relationship(
        back_populates="ratee",
        sa_relationship_kwargs={"foreign_keys": "[Rating.ratee_id]", "cascade": "all, delete-orphan"}
    )
    admin_logs: Mapped[List["AdminLog"]] = Relationship(back_populates="admin", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    otps: Mapped[List["OtpModel"]] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

from src.brand.models import BrandProfile
from src.influencer.models import InfluencerProfile
from src.event.models import Event, EventApplication
from src.chat.models import Message
from src.notification.models import Notification
from src.ratings.models import Rating
from src.admin_logs.models import AdminLog
from src.otp.models import OtpModel
from src.admin.models import Admin

Users.update_forward_refs()
