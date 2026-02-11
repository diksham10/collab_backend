# function to be used in other models
from fastapi import Depends, HTTPException, status, Cookie, Request,Response, WebSocket
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional,List
from jose import jwt, JWTError, ExpiredSignatureError
from src.auth.models import Users
from src.auth.service import create_access_token,create_refresh_token, refresh_access_token
from src.database import get_session
from uuid import UUID
from datetime import datetime, timezone
from dotenv import load_dotenv
from os import getenv
load_dotenv()

SECRET_KEY = getenv("SECRET_KEY")
ALGORITHM = getenv("ALGORITHM")

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/login")

async def get_current_user(request: Request,response: Response, db: AsyncSession = Depends(get_session)) -> Users:
    """
    Extract current logged-in user from JWT token.
    """
    print("fuck you")
    token = request.cookies.get("access_token")
    # print(f"Retrieved token from cookies: {token}")
    refresh_token = request.cookies.get("refresh_token")
    # print(f"Retrieved refresh token from cookies: {refresh_token}")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print("fuck you")
        user_id: UUID = UUID(payload.get("sub"))
        print("fuck you")
        
    except:   
        print("if no access token or token expired")
        if not refresh_token:
            raise HTTPException(status_code=401, detail="Token expired and no refresh token provided")
        try:
            new_token =await refresh_access_token(refresh_token, db, response)
            print(f"New token after refresh: {new_token}")
            if not new_token:
                raise HTTPException(status_code=401, detail="Invalid refresh token and no new token created")
            
            response.set_cookie(
                key="access_token",
                value=new_token,
                httponly=True,
                max_age=15*60,
                secure=True,
                samesite="None"
            )
            payload = jwt.decode(new_token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: UUID = UUID(payload.get("sub"))
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token after refresh")
        except ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    
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

async def get_current_user_ws(websocket: WebSocket, db: AsyncSession) -> Users:
    """
    Extract current user from JWT cookie for WebSocket connection
    """
    token = websocket.cookies.get("access_token")
    if not token:
        await websocket.close(code=1008)
        raise Exception("Not authenticated")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: UUID = payload.get("sub")
        if not user_id:
            await websocket.close(code=1008)
            raise Exception("Invalid token")
    except ExpiredSignatureError:
        await websocket.close(code=1008)
        raise Exception("Token expired")
    except JWTError as e:
        await websocket.close(code=1008)
        raise Exception(f"JWT error: {e}")

    result = await db.execute(select(Users).where(Users.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        await websocket.close(code=1008)
        raise Exception("User not found")
    return user
