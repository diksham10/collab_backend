# pydantic data validation for various user activities such as creation login token
from pydantic import BaseModel
from typing import Optional
import datetime
from src.myenums import UserRole
from uuid import UUID


#for registering user
class UserCreate(BaseModel):
    email: str
    username: str
    password: str
    role: UserRole

#for logging in user
class UserLogin(BaseModel):
    email: str
    password: str

#for returning 
class UserRead(BaseModel):
    id: UUID
    username: str
    email:str
    role: UserRole
    is_active: bool
    
    model_config ={
        "from_attributes": True
    }

#for updating user
class UserUpdate(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[UserRole] = None

#for changing password
class ChangePassword(BaseModel):
    old_password: str
    new_password: str

#for resetting password
class ResetPassword(BaseModel):
    email: str
    new_password: str


#for token
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"   

