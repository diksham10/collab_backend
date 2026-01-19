# pydantic data validation for various user activities such as creation login token
from pydantic import BaseModel, EmailStr
from typing import Optional
import datetime
from src.myenums import UserRole
from uuid import UUID



#for registering user
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    role: UserRole

#for logging in user
class UserLogin(BaseModel):
    username: str
    password: str

#for returning 
class UserRead(BaseModel):
    username: str
    email:EmailStr
    role: UserRole
    is_active: bool
    is_verified: bool
    
    model_config ={
        "from_attributes": True
    }

#for updating user
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[UserRole] = None

#for changing password
class ChangePassword(BaseModel):
    old_password: str
    new_password: str

#for resetting password
class ResetPassword(BaseModel):
    email: EmailStr
    new_password: str


#for token
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"   


class RegisterResponse(BaseModel):
    email: str
    message: str
    auth_token: Optional[str] = None
    
