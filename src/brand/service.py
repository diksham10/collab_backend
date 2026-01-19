from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from fastapi import HTTPException, Depends
from src.brand.schema import BrandCreate, BrandRead, BrandUpdate
from src.auth.models import Users
from src.brand.models import BrandProfile
from datetime import datetime, timedelta, timezone
from src.auth.dependencies import get_current_user



async def create_brand( brand_data: BrandCreate, current_user: Users, db: AsyncSession ) :
    

    if current_user.role != "brand":
        raise HTTPException(status_code=403, detail="Only brand users can create brands")  
    result1 = await db.execute(select(BrandProfile).where(BrandProfile.user_id == current_user.id))
    brand_count = len(result1.scalars().all())
    if brand_count >=4:
        raise HTTPException(status_code=403, detail="Brand limit reached. Cannot create more brands.") 
     
    new_brand = BrandProfile(

        user_id = current_user.id,
        name = brand_data.name,
        location= brand_data.location,
        description = brand_data.description,
        website_url = brand_data.website_url,
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat()
    )
    try:
        db.add(new_brand)
        await db.commit()
        await db.refresh(new_brand)
        return new_brand
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create brand")
    
async def get_brands(current_user: Users=Depends(get_current_user), db: AsyncSession=Depends())-> BrandRead:

    result = await db.execute(select(BrandProfile).where(BrandProfile.user_id == current_user.id))
    brands = result.scalars().all()
    if not brands:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brands   


async def update_brand(current_user: Users, brand_id: str, brand_data: BrandUpdate, db: AsyncSession):
    result = await db.execute(select(Users).where(Users.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role != "brand":
        raise HTTPException(status_code=403, detail="Only brand users can update brands")
    result1 = await db.execute(select(BrandProfile).where(BrandProfile.user_id == current_user.id, BrandProfile.id == brand_id))
    brand = result1.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    if brand_data.name is not None:
        brand.name = brand_data.name
    if brand_data.description is not None:
        brand.description = brand_data.description
    if brand_data.website_url is not None:
        brand.website_url = brand_data.website_url
    brand.updated_at = datetime.utcnow().isoformat()
    try:
        db.add(brand)
        await db.commit()
        await db.refresh(brand)
        return brand
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update brand")


async def delete_brand(current_user: Users, brand_id: str, db: AsyncSession):
    result = await db.execute(select(Users).where(Users.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role != "brand":
        raise HTTPException(status_code=403, detail="Only brand users can delete brands")
    result1 = await db.execute(select(BrandProfile).where(BrandProfile.user_id == current_user.id, BrandProfile.id == brand_id))
    brand = result1.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    try:
        await db.delete(brand)
        await db.commit()
        return True
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete brand")

