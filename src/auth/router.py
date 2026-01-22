#create api router in this.
from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from typing import Optional
from fastapi.security import OAuth2PasswordRequestForm

from src.auth.schema import UserCreate,RegisterResponse, UserLogin, UserRead, UserUpdate, ChangePassword, ResetPassword, Token
from src.auth.service import create_user, authenticate_user, create_access_token, update_user, change_password, reset_password, create_refresh_token, refresh_access_token
from src.database import get_session
from src.auth.models import Users
from src.auth.dependencies import get_current_user
from src.otp.service import create_send_otp

router = APIRouter(prefix="/user", tags=["user"])


#reegister endpoint
@router.post("/register", response_model=RegisterResponse)
async def register(user_in: UserCreate,response: Response, db: AsyncSession = Depends(get_session)):
    print(f"user registration called  {user_in}")
    result=await db.execute(select(Users).where(Users.email == user_in.email))
    user_exists= result.scalars().first()
    if user_exists:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = await create_user(user_in, db)
    await create_send_otp(db, new_user, subject="Verify your email")
    auth_token = create_access_token(new_user.id, new_user.role)
    refresh_token = create_refresh_token(new_user.id)

    response.set_cookie(
        key="access_token",
        value=auth_token,
        httponly=True,
        max_age=15*60,
        secure=True,
        samesite="None"
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=7*24*3600,
        secure=True,
        samesite="None"
    )
    return RegisterResponse(email=new_user.email, message="User registered successfully. Please verify your email.", auth_token=auth_token)


@router.post("/login", response_model=Token)
async def login(
    user_in: UserLogin,
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_session)
):
    
    user = await authenticate_user(user_in.username, user_in.password, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id)
    print("Setting cookies...", access_token, refresh_token)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=15*60*60,
        secure=True,
        samesite="None"
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=7*24*3600,
        secure=True,
        samesite="None"
    )
    
    return Token(access_token=access_token, token_type="bearer")
    
    print(f"Token set in cookies: {access_token}")
    

#get current user endpoint
@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: Users = Depends(get_current_user)):
    return current_user


#update current user endpoint
@router.put("/me", response_model=UserRead)
async def update_current_user(
    user_in: UserUpdate,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    updated_user = await update_user(current_user, user_in, db)
    return updated_user


#change password endpoint
@router.post("/me/change-password", response_model=UserRead)
async def change_current_password(password_data: ChangePassword, current_user: Users = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    try:
        updated_user = await change_password(current_user, password_data, db)
        return updated_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


#reset password endpoint
@router.post("/reset-password", response_model=UserRead)
async def reset_password_endpoint(reset_data: ResetPassword, db: AsyncSession = Depends(get_session)):
    user = await reset_password(reset_data.email, reset_data.new_password, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# # OAuth2 token endpoint for Swagger UI
# @router.post("/token", response_model=Token, summary="Get Token (OAuth2)")
# async def get_token(
#     username: str = Form(..., description="Email address"),
#     password: str = Form(...),
#     grant_type: Optional[str] = Form(None),
#     scope: str = Form(""),
#     client_id: Optional[str] = Form(None),
#     client_secret: Optional[str] = Form(None),
#     db: AsyncSession = Depends(get_session)
# ):
#     """
#     OAuth2 compatible token endpoint for Swagger UI.
#     This endpoint accepts form-data (application/x-www-form-urlencoded).
    
#     Use the 🔓 Authorize button in Swagger to test this.
#     """
#     user = await authenticate_user(username, password, db)
#     if not user:
#         raise HTTPException(
#             status_code=401,
#             detail="Invalid email or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )

#     auth_token = create_access_token(user.id, user.role)
#     refresh_token = create_refresh_token(user.id)

#     Response.set_cookie(
#         key="access_token",
#         value=auth_token,
#         httponly=True,
#         max_age=15*60,
#         secure=True,
#         samesite="Lax"
#     )
#     Response.set_cookie(
#         key="refresh_token",
#         value=refresh_token,
#         httponly=True,
#         max_age=7*24*3600,
#         secure=True,
#         samesite="Lax"
#     )
#     return {"access_token": auth_token, "token_type": "bearer"}


#get all users endpoint
@router.get("/all_users", response_model=list[UserRead])
async def get_all_users( db: AsyncSession = Depends(get_session)):

    result = await db.execute(select(Users))
    users = result.scalars().all()
    return users


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key="access_token",
        path="/",
        samesite="none",
        secure=True   # True in production HTTPS
    )
    response.delete_cookie(
        key="refresh_token",
        path="/",
        samesite="none",
        secure=True
    )
    return {"message": "Logged out"}
