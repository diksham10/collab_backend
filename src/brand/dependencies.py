from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.auth.dependencies import get_current_user
from src.database import get_session
from src.auth.models import Users
from src.brand.models import BrandProfile


async def check_brand_limit(
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    result = await db.execute(
        select(BrandProfile).where(BrandProfile.user_id == current_user.id)
    )
    brand_count = len(result.scalars().all())

    if brand_count >= 4:
        raise HTTPException(
            status_code=400,
            detail="Brand limit reached. Cannot create more brands."
        )
