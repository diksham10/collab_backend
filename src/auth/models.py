from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from src.myenums import UserRole
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from src.brand.models import BrandProfile
    from influencer.models import InfluencerProfile
    from event.models import Event, EventApplication
    from chat.models import Message
    from notification.models import Notification
    from ratings.models import Rating
    from admin_logs.models import AdminLog
    from otp.models import OtpModel
    

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
    
    brand_profile: Optional["BrandProfile"] = Relationship(back_populates="user")
    influencer_profile: Optional["InfluencerProfile"] = Relationship(back_populates="user")
    # events: List["Event"] = Relationship(back_populates="brand")
    # applications: List["EventApplication"] = Relationship(back_populates="influencer")
    sent_messages: List["Message"] = Relationship(
        back_populates="sender",
        sa_relationship_kwargs={"foreign_keys": "[Message.sender_id]"}
    )
    received_messages: List["Message"] = Relationship(
        back_populates="receiver",
        sa_relationship_kwargs={"foreign_keys": "[Message.receiver_id]"}
    )
    notifications: List["Notification"] = Relationship(back_populates="user")
    ratings_given: List["Rating"] = Relationship(
        back_populates="rater",
        sa_relationship_kwargs={"foreign_keys": "[Rating.rater_id]"}
    )
    ratings_received: List["Rating"] = Relationship(
        back_populates="ratee",
        sa_relationship_kwargs={"foreign_keys": "[Rating.ratee_id]"}
    )
    admin_logs: List["AdminLog"] = Relationship(back_populates="admin")
    otps: List["OtpModel"] = Relationship(back_populates="user")

from src.brand.models import BrandProfile
from src.influencer.models import InfluencerProfile
from src.event.models import Event, EventApplication
from src.chat.models import Message
from src.notification.models import Notification
from src.ratings.models import Rating
from src.admin_logs.models import AdminLog
from src.otp.models import OtpModel

Users.update_forward_refs()
