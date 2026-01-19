from pydantic import BaseModel
from typing import Optional
from src.myenums import UserRole
from uuid import UUID

class BrandCreate(BaseModel):
    name: str
    description: Optional[str]=None
    location: Optional[str]=None
    website_url: Optional[str]=None
    created_at : Optional[str]=None
    updated_at: Optional[str]=None


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
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    website_url: Optional[str] = None
    updated_at: Optional[str] = None




    

