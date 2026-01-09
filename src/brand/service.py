from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from fastapi import HTTPException
from src.brand.schema import BrandCreate, BrandRead
from src.auth.models import Users
from src.brand.models import BrandProfile


# to create a brand limit= 4
async def create_brand(current_user: Users, brand_data: BrandCreate, db: AsyncSession):

    result = await db.execute(select(Users).where(Users.id == current_user.id))
    user = result.scalar_one_or_none()

    result1 = await db.execute(select(BrandProfile).where(BrandProfile.user_id == current_user.id))
    brand_count = len(result1.scalars().all())
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role != "brand":
        raise HTTPException(status_code=403, detail="Only brand users can create brands")   
    if brand_count >= 4:
        raise HTTPException(status_code=400, detail="Brand limit reached. Cannot create more brands.")
    new_brand = BrandProfile(
        user_id = current_user.id,
        brand_name = brand_data.brand_name,
        brand_description = brand_data.brand_description
        


    )




