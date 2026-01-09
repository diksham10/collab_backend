#create api router in this.
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi.security import OAuth2PasswordBearer
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from src.auth.schema import UserCreate,RegisterResponse, UserLogin, UserRead, UserUpdate, ChangePassword, ResetPassword, Token
from src.auth.service import create_user, authenticate_user, create_access_token, update_user, change_password, reset_password
from src.database import get_session
from src.auth.models import Users
from src.auth.dependencies import get_current_user
from src.otp.service import create_send_otp, verify_otp

router = APIRouter(prefix="/user", tags=["user"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/login")


@router.post("/register", response_model=RegisterResponse)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_session)):
    print(f"user registration called  {user_in}")
    result=await db.execute(select(Users).where(Users.email == user_in.email))
    user_exists= result.scalars().first()
    if user_exists:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = await create_user(user_in, db)
    await create_send_otp(db, new_user, subject="Verify your email")
    auth_token = create_access_token(new_user.id)
    return RegisterResponse(message="User registered successfully. Please verify your email.", auth_token=auth_token)


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_session)
):
    # form_data.username is the email
    user = await authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(user.id)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: Users = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserRead)
async def update_current_user(
    user_in: UserUpdate,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    updated_user = await update_user(current_user, user_in, db)
    return updated_user


@router.post("/me/change-password", response_model=UserRead)
async def change_current_password(password_data: ChangePassword, current_user: Users = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    try:
        updated_user = await change_password(current_user, password_data, db)
        return updated_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reset-password", response_model=UserRead)
async def reset_password_endpoint(reset_data: ResetPassword, db: AsyncSession = Depends(get_session)):
    user = await reset_password(reset_data.email, reset_data.new_password, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


    