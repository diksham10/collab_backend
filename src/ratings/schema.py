from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class RatingCreate(BaseModel):
    id: Optional[UUID] 
    rater_id: Optional[UUID] 
    ratee_id: Optional[UUID] 
    event_id: Optional[UUID] = None
    score: Optional[float] = None
    review: Optional[str] = None
    created_at: datetime = None

class RatingUpdate(BaseModel):
    id: Optional[UUID] 
    rater_id: Optional[UUID] 
    ratee_id: Optional[UUID] 
    event_id: Optional[UUID] = None
    score: Optional[float] = None
    review: Optional[str] = None
    created_at: datetime = None

class RatingRead(BaseModel):
    id: UUID
    rater_id: UUID
    ratee_id: UUID
    event_id: Optional[UUID] = None
    score: Optional[float] = None
    review: Optional[str] = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

class ratingAvgRead(BaseModel):
    ratee_id: UUID
    average_score: float

    model_config = {
        "from_attributes": True
    }
        