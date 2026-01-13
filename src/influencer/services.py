from fastapi import Depends, HTTPException
from sqlmodel import select
from src.influencer.schema import InfluencerCreate, InfluencerRead, InfluencerUpdate, SocialLinkCreate, SocialLinkRead, SocialLinkUpdate
from src.influencer.models import InfluencerProfile, SocialLink
from src.auth.models import Users
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession


async def create_influencer(current_user: Users, influencer: InfluencerCreate, db:AsyncSession):

    result = await  db.execute(select(Users).where(Users.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role != "influencer":
        raise HTTPException(status_code=403, detail="Only influencer users can create influencer profiles")
    new_influencer = InfluencerProfile(
        user_id = current_user.id,
        name = influencer.name,
        niche = influencer.niche,
        audience_size = influencer.audience_size,
        engagement_rate = influencer.engagement_rate,
        bio = influencer.bio,
        location = influencer.location,
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat()
    )
    try:
        db.add(new_influencer)
        await db.commit()
        await db.refresh(new_influencer)
        return new_influencer
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create influencer profile")

async def get_influencer(current_user: Users, db: AsyncSession) -> InfluencerRead:

    result = await db.execute(select(InfluencerProfile).where(InfluencerProfile.user_id == current_user.id))
    influencer = result.scalar_one_or_none()
    if not influencer:
        raise HTTPException(status_code=404, detail="Influencer profile not found")
    return influencer

async def update_influencer(current_user: Users, influencer_id: str, influencer_data: InfluencerUpdate, db: AsyncSession) -> InfluencerRead:
    result = await db.execute(select(Users).where(Users.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role != "influencer":
        raise HTTPException(status_code=403, detail="Only influencer users can update influencer profiles")
    result1 = await db.execute(select(InfluencerProfile).where(InfluencerProfile.user_id == current_user.id, InfluencerProfile.id == influencer_id))
    influencer = result1.scalar_one_or_none()
    if not influencer:
        raise HTTPException(status_code=404, detail="Influencer profile not found")
    
    influencer.name = influencer_data.name
    influencer.niche = influencer_data.niche
    influencer.audience_size = influencer_data.audience_size
    influencer.engagement_rate = influencer_data.engagement_rate
    influencer.bio = influencer_data.bio
    influencer.location = influencer_data.location
    influencer.updated_at = datetime.utcnow().isoformat()
    try:
        db.add(influencer)
        await db.commit()
        await db.refresh(influencer)
        return influencer
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update influencer profile")


# Function for creating , updating ,getting and deleting social links

async def get_social_links(current_user: Users, db: AsyncSession) -> SocialLinkRead:
    result = await db.execute(select(InfluencerProfile).where(InfluencerProfile.user_id == current_user.id))
    influencer = result.scalar_one_or_none()
    if not influencer:
        raise HTTPException(status_code=404, detail="Influencer profile not found")
    result1 = await db.execute(select(SocialLink).where(SocialLink.influencer_profile_id == influencer.id))
    social_links = result1.scalars().all()
    if not social_links:
        raise HTTPException(status_code=404, detail="Social links not found")
    return social_links 


async def create_social_link(current_user: Users, social_link_data: SocialLinkCreate , db: AsyncSession):
    result = await db.execute(select(InfluencerProfile).where(InfluencerProfile.user_id == current_user.id))
    influencer = result.scalar_one_or_none()
    if not influencer:
        raise HTTPException(status_code=404, detail="Influencer profile not found")
    
    new_social_link = SocialLink(
        influencer_profile_id=influencer.id,
        platform=social_link_data.platform,
        url=social_link_data.url,
        followers=social_link_data.followers,
        linked_at=datetime.utcnow().isoformat()
    )
    
    try:
        db.add(new_social_link)
        await db.commit()
        await db.refresh(new_social_link)
        return new_social_link
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create social link")



async def update_social_link(current_user: Users, social_link_id: str, social_link_data: SocialLinkUpdate, db: AsyncSession):
    result = await db.execute(select(InfluencerProfile).where(InfluencerProfile.user_id == current_user.id))
    influencer = result.scalar_one_or_none()
    if not influencer:
        raise HTTPException(status_code=404, detail="Influencer profile not found")
    
    result1 = await db.execute(select(SocialLink).where(SocialLink.influencer_profile_id == influencer.id, SocialLink.id == social_link_id))
    social_link = result1.scalar_one_or_none()
    if not social_link:
        raise HTTPException(status_code=404, detail="Social link not found")
    
    if social_link_data.platform is not None:
        social_link.platform = social_link_data.platform
    if social_link_data.url is not None:
        social_link.url = social_link_data.url
    if social_link_data.followers is not None:
        social_link.followers = social_link_data.followers
    social_link.linked_at = datetime.utcnow().isoformat()
    
    try:
        db.add(social_link)
        await db.commit()
        await db.refresh(social_link)
        return social_link
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update social link")
    

async def delete_social_link(current_user: Users, social_link_id: str, db: AsyncSession):       
    result = await db.execute(select(InfluencerProfile).where(InfluencerProfile.user_id == current_user.id))
    influencer = result.scalar_one_or_none()
    if not influencer:
        raise HTTPException(status_code=404, detail="Influencer profile not found")
    
    result1 = await db.execute(select(SocialLink).where(SocialLink.influencer_profile_id == influencer.id, SocialLink.id == social_link_id))
    social_link = result1.scalar_one_or_none()
    if not social_link:
        raise HTTPException(status_code=404, detail="Social link not found")
    
    try:
        await db.delete(social_link)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete social link")
