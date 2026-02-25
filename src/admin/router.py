from src.admin.models import Admin
from src.auth.dependencies import get_current_user
from src.auth.models import Users
from src.database import get_session
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router = APIRouter()



@router.get("/me", response_model=Admin)
async def get_my_admin_info(current_user: Users = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not an admin user")
    
    result = await db.execute(select(Admin).where(Admin.user_id == current_user.id))
    admin_info = result.scalar_one_or_none()
    if not admin_info:
        raise HTTPException(status_code=404, detail="Admin info not found")
    
    return admin_info

