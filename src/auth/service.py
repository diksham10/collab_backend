# passworf verify authentication creating token type functions in this
from src.auth.schema import UserCreate,UserUpdate,ChangePassword, ResetPassword
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.auth.models import Users
from passlib.context import CryptContext
from fastapi import HTTPException, status, Response
from typing import Optional
from jose import jwt,JWTError
from datetime import datetime, timedelta, timezone
from psycopg2 import IntegrityError
from dotenv import load_dotenv
import os
from uuid import UUID
from src.refresh_token.model import RefreshTokenModel
from src.refresh_token.service import hash_token, delete_refresh_token, save_refresh_token

load_dotenv()

SECRET_KEY=os.getenv("SECRET_KEY")
ALGORITHM=os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
def hash_password(password: str) -> str:
    hashed_password = pwd_context.hash(password)
    return hashed_password
def verify_password(plain_password: str, hashed_password: str)-> bool:
    return pwd_context.verify(plain_password, hashed_password)

async def create_user(user_in: UserCreate, db: AsyncSession ) -> Users:
    hashed_password = hash_password(user_in.password)
    try :
        result =await db.execute(select(Users).where(Users.username == user_in.username))
        user_exists= result.scalars().first()
        if user_exists: 
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )   
    new_user = Users(   
        email = user_in.email,
        username= user_in.username,
        hashed_password= hashed_password,
        role = user_in.role
    )
    db.add(new_user)
    try:
        await db.commit()
        await db.refresh(new_user)
        return new_user
    except IntegrityError as e:
        await db.rollback()
        # handle unique constraint violations for email/username
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already exists"
        )

import logging

logger = logging.getLogger(__name__)

async def   authenticate_user(
    identifier: str,
    password: str,
    db: AsyncSession
) -> Optional[Users]:
    try:
        # Fetch the user asynchronously
        result = await db.execute(
        select(Users).where(
            or_(                        #it is tio check either username or email
                Users.email == identifier,
                Users.username == identifier
            )
        )
    )
        user = result.scalars().first()

        if not user:
            logger.info(f"Authentication failed: user not found for email {identifier}")
            return None

        # Verify password
        if not verify_password(password, user.hashed_password):
            logger.info(f"Authentication failed: incorrect password for email {identifier}")
            return None
        
        if not user.is_active:
            logger.info(f"Authentication failed: inactive user for email {identifier}")
            return None
        if not user.is_verified:
            logger.info(f"Authentication failed: unverified user for email {identifier}")
            return None
        
        return user
    

    except Exception as e:
        logger.error(f"Authentication error for email {identifier}: {str(e)}", exc_info=True)
        return None


def create_access_token(user_id:str, user_role:str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),
        "role": user_role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=7)  # Refresh token valid for 7 days

    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token    


async def update_user(user: Users, user_in: UserUpdate, db: AsyncSession) -> Users:
    if user_in.email is not None:
        user.email = user_in.email

    if user_in.password: 
        user.hashed_password = hash_password(user_in.password)

    if user_in.role is not None:
        user.role = user_in.role  # or UserRole(user_in.role) if needed

    user.updated_at = datetime.utcnow()

    # db.add(user)  # unnecessary if user is already in session
    await db.commit()
    await db.refresh(user)
    return user


async def change_password(user: Users, password: ChangePassword, db: AsyncSession) -> Users:
    if not verify_password(password.old_password, user.hashed_password):
        raise ValueError("Old password is incorrect")
    user.hashed_password = hash_password(password.new_password)
    user.updated_at = datetime.utcnow()
    db. add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def reset_password(email: str, new_password: str, db: AsyncSession) -> Optional[Users]:
    result = await db.execute(
        select(Users).where(Users.email == email)
    )
    user = result.scalars().first()
    if not user:
        raise ValueError("User with this email does not exist")
    
    user.hashed_password = hash_password(new_password)
    user.updated_at = datetime.utcnow()
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def refresh_access_token(refresh_token: str, db: AsyncSession,response: Response) -> Optional[str]:
    import os
    IS_PRODUCTION = os.getenv("ENV","development") == "production"
    print("Refreshing access token...")
    hashed_token = await hash_token(refresh_token)
    print(f"Hashed refresh token: {hashed_token}")
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[str] = payload.get("sub")        
        print(f"Decoded user_id from refresh token: {user_id}")
        if not user_id:
            print("No user_id found in token payload")
            return None


        result = await db.execute(
            select(RefreshTokenModel).where(
                RefreshTokenModel.user_id == user_id,
            )
        )

        token_entry = result.scalars().first()
        print(f"Token entry from DB: {token_entry}")
        if not token_entry:
            return None
        if token_entry.expires_at < datetime.utcnow():
            await delete_refresh_token(hashed_token, db)
            return None

        
        
        result = await db.execute(select(Users).where(Users.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            print("User not found for the given user_id")
            return None
        new_access_token = create_access_token(user_id, user.role)
        # validate old token and rotate
        await delete_refresh_token(token_entry.user_id, db)
        new_refresh_token = create_refresh_token(user_id)
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            max_age=7*24*3600,
            domain=".dixam.me" if IS_PRODUCTION else None,
            secure=IS_PRODUCTION,
            samesite="None" if IS_PRODUCTION else "Lax",
            path="/"
        )
        print("the new_access_token", new_access_token)
        print("the new_refresh_token", new_refresh_token)
        await save_refresh_token(UUID(user_id), await hash_token(new_refresh_token), db)
        return new_access_token
    except JWTError:
        return None




