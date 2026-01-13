from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from src.myenums import SocialPlatform


class InfluencerCreate(BaseModel):
    name: str
    niche: Optional[str] = None
    audience_size: Optional[int] = None
    engagement_rate: Optional[float] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class InfluencerRead(BaseModel):
    id: UUID 
    name: str
    niche: Optional[str] = None
    audience_size: Optional[int] = None
    engagement_rate: Optional[float] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {
        "from_attributes": True
    }

class InfluencerUpdate(BaseModel):
    name: Optional[str] = None
    niche: Optional[str] = None
    audience_size: Optional[int] = None
    engagement_rate: Optional[float] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    updated_at: Optional[str] = None

#socaial link schema
class SocialLinkCreate(BaseModel):
    platform: SocialPlatform
    url: str
    followers: Optional[int] = None
    linked_at: Optional[str] = None 


class SocialLinkRead(BaseModel):
    id: UUID
    influencer_profile_id: UUID
    platform: str
    url: str
    followers: Optional[int] = None
    linked_at: Optional[str] = None

    model_config = {
        "from_attributes": True
    }
    
class SocialLinkUpdate(BaseModel):
    platform: Optional[SocialPlatform] = None
    url: Optional[str] = None
    followers: Optional[int] = None
    linked_at: Optional[str] = None