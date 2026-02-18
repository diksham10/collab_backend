from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime, date

class EventCreate(BaseModel):

    title: str
    description: Optional[str] = None
    objectives: Optional[str] = None
    budget: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] =None
    deliverables: Optional[str] = None
    target_audience: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = "active"
   
class EventRead(BaseModel):
    id: UUID 
    user_id: UUID 
    brand_id: UUID
    title: str
    description: Optional[str] = None
    objectives: Optional[str] = None
    budget: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    deliverables: Optional[str] = None
    target_audience: Optional[str] = None
    category: Optional[str] = None
    location: str 
    status: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    objectives: Optional[str] = None
    budget: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    deliverables: Optional[str] = None
    target_audience: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    event_active: Optional[bool] = None

class EventApplicationCreate(BaseModel):
    event_id: UUID
    influencer_id: UUID


class EventMiniRead(BaseModel):
    id: UUID 
    title: str

class InfluencerMiniRead(BaseModel):
    id: UUID 
    name: str

class EventApplicationInfo(BaseModel):
    event : EventMiniRead
    influencer : InfluencerMiniRead
    applied_at: datetime
    status: str

class EventApplicationRead(BaseModel):

    id: UUID
    event_id: UUID
    influencer_id: UUID

    status: str
    applied_at: datetime

    model_config = {
        "from_attributes": True
    }



class EventApplicationStatusUpdate(BaseModel):
    status: Optional[str] = None

class UserPreference(BaseModel):
    location: Optional[str] = None
    categories: Optional[list[str]] = None
    budget_range: Optional[tuple[float, float]] = None
    target_audience: Optional[str] = None
    start_date: Optional[date] = None

