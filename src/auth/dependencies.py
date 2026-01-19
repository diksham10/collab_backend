# function to be used in other models
from fastapi import Depends, HTTPException, status, Cookie, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional,List
from jose import jwt, JWTError, ExpiredSignatureError
from src.auth.models import Users
from src.database import get_session
from uuid import UUID
from dotenv import load_dotenv
from os import getenv
load_dotenv()

SECRET_KEY = getenv("SECRET_KEY")
ALGORITHM = getenv("ALGORITHM")

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/login")

async def get_current_user(request: Request, db: AsyncSession = Depends(get_session)) -> Users:
    """
    Extract current logged-in user from JWT token.
    """
    token = request.cookies.get("access_token")
    print(f"Retrieved token from cookies: {token}")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")    
    try:
        print("Decoding token...")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[UUID] = payload.get("sub")
     
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid user ID in token")
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError as e:
        raise HTTPException(status_code=401, detail=str(e))
    
    result = await db.execute(select(Users).where(Users.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def role_required(role: str):
    async def dependency(current_user: Users = Depends(get_current_user)):
        if current_user.role != role:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return dependency

