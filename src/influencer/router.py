from fastapi import APIRouter, Depends
from src.auth.dependencies import get_current_user
from src.auth.models import Users
from src.influencer.services import create_influencer, update_influencer, get_influencer, create_social_link, get_social_links, delete_social_link
from src.influencer.schema import InfluencerCreate, InfluencerRead, InfluencerUpdate, SocialLinkRead, SocialLinkCreate
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session

router = APIRouter()

@router.post("/create_influencerprofile", response_model= InfluencerRead)
async def create_influencerprofile( influencer_in: InfluencerCreate,current_user: Users =Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    new_influencer = await create_influencer(current_user,influencer_in,db)
    return new_influencer


@router.get("/get_influencer_by_user", response_model= InfluencerRead)
async def get_influencerprofile(current_user: Users = Depends(get_current_user), db: AsyncSession=Depends(get_session)):
    influencer = await get_influencer(current_user, db)
    return influencer

@router.put("/update_influencerprofile/{influencer_id}", response_model= InfluencerRead)
async def update_influencerprofile(influencer_id: str, influencer_in: InfluencerUpdate, current_user: Users =Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    updated_influencer = await update_influencer(current_user, influencer_id, influencer_in, db)
    return updated_influencer
 

#routers for socal media links

@router.post("/create_sociallink", response_model= SocialLinkRead)
async def create_sociallink(sociallink_in: SocialLinkCreate, current_user: Users = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    new_sociallink = await create_social_link(current_user, sociallink_in, db)
    return new_sociallink

@router.get("/get_sociallinks", response_model= list[SocialLinkRead])
async def get_sociallinks(current_user: Users = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    social_links = await get_social_links(current_user, db)
    return social_links

@router.put("/update_influencerprofile/{influencer_id}", response_model= InfluencerRead )
async def update_influencerprofile(influencer_id: str, influencer_in: InfluencerUpdate, current_user: Users =Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    updated_influencer = await update_influencer(current_user, influencer_id, influencer_in, db)
    return updated_influencer

@router.delete("/delete_sociallink/{sociallink_id}")
async def delete_sociallink(sociallink_id: str, current_user: Users =Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    await delete_social_link(current_user, sociallink_id, db)
    return {"message": "Social link deleted successfully"}  
