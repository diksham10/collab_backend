from pydantic import BaseModel
from typing import Optional
from src.myenums import UserRole
from uuid import UUID

class BrandCreate(BaseModel):
    name: str
    description: Optional[str]
    location: Optional[str]
    website_url: Optional[str]
    created_at : Optional[str]
    updated_at: Optional[str]


class BrandRead(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    location: Optional[str]
    website_url: Optional[str]
    created_at : Optional[str]
    updated_at: Optional[str]
    
    model_config = {
        "from_attributes": True
    }

class BrandUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    location: Optional[str]
    website_url: Optional[str]
    updated_at: Optional[str]




    

