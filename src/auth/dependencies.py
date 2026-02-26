from fastapi import Depends, HTTPException, status, Cookie, Request, Response, WebSocket
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional, List
from jose import jwt, JWTError, ExpiredSignatureError
from src.auth.models import Users
from src.auth.service import create_access_token, create_refresh_token, refresh_access_token
from src.database import get_session
from uuid import UUID
from datetime import datetime, timezone
from dotenv import load_dotenv
from os import getenv
import os

load_dotenv()

SECRET_KEY = getenv("SECRET_KEY")
ALGORITHM = getenv("ALGORITHM")
IS_PRODUCTION = os.getenv("ENV", "development") == "production"


async def get_current_user(request: Request, response: Response, db: AsyncSession = Depends(get_session)) -> Users:
    """
    Extract current logged-in user from JWT token.
    """
    token = request.cookies.get("access_token")
    refresh_token = request.cookies.get("refresh_token")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: UUID = UUID(payload.get("sub"))
        # print(f"✅ Access token valid for user: {user_id}")  # ✅ Optional: keep for debugging
        
    except:   
        print("⚠️ Access token invalid/expired, attempting refresh...")
        if not refresh_token:
            # Clear cookies and force re-login
            response.delete_cookie("access_token", domain=".dixam.me" if IS_PRODUCTION else None, path="/")
            response.delete_cookie("refresh_token", domain=".dixam.me" if IS_PRODUCTION else None, path="/")
            raise HTTPException(
                status_code=401, 
                detail="Session expired. Please login again.",
                headers={"X-Session-Expired": "true"}
            )
        
        print("Refreshing access token")
        try:
            new_token = await refresh_access_token(refresh_token, db, response)
            # print(f"New token after refresh: {new_token is not None}")
            
            if not new_token:
                # Refresh token not found or invalid - clear cookies
                response.delete_cookie("access_token", domain=".dixam.me" if IS_PRODUCTION else None, path="/")
                response.delete_cookie("refresh_token", domain=".dixam.me" if IS_PRODUCTION else None, path="/")
                raise HTTPException(
                    status_code=401, 
                    detail="Session invalid. Please login again.",
                    headers={"X-Session-Expired": "true"}
                )
            
            # Set new access token in cookie
            response.set_cookie(
                key="access_token",
                value=new_token,
                httponly=True,
                max_age=15*60,
                domain=".dixam.me" if IS_PRODUCTION else None,
                secure=IS_PRODUCTION,
                samesite="None" if IS_PRODUCTION else "Lax",
                path="/"
            )
            
            payload = jwt.decode(new_token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: UUID = UUID(payload.get("sub"))
            
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token after refresh")
                
            print(f"✅ Token refreshed for user: {user_id}")
            
        except HTTPException:
            raise
        except ExpiredSignatureError:
            response.delete_cookie("access_token", domain=".dixam.me" if IS_PRODUCTION else None, path="/")
            response.delete_cookie("refresh_token", domain=".dixam.me" if IS_PRODUCTION else None, path="/")
            raise HTTPException(
                status_code=401, 
                detail="Refresh token expired. Please login again.",
                headers={"X-Session-Expired": "true"}
            )
        except Exception as e:
            print(f"❌ Refresh error: {e}")
            response.delete_cookie("access_token", domain=".dixam.me" if IS_PRODUCTION else None, path="/")
            response.delete_cookie("refresh_token", domain=".dixam.me" if IS_PRODUCTION else None, path="/")
            raise HTTPException(
                status_code=401, 
                detail="Authentication failed. Please login again.",
                headers={"X-Session-Expired": "true"}
            )
    
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




def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        exp = payload.get("exp")
        if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
            return None

        return payload

    except JWTError:
        return None
 
async def get_current_user_ws(websocket: WebSocket, db: AsyncSession):
    # Read token from cookie
    token = websocket.cookies.get("access_token")
    refresh_token = websocket.cookies.get("refresh_token")
    # print('🔑 WebSocket token: ', refreshtoken)

    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        # Decode the JWT first
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload:
            return None
        

    user_id = payload.get("sub")
    if not user_id:
        return None

    user = await db.get(Users, UUID(user_id))
    return user