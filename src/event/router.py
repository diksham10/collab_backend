from fastapi import APIRouter,Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.dependencies import get_current_user
from src.auth.models import Users
from src.event.schema import EventApplicationCreate, EventApplicationRead, EventApplicationStatusUpdate, EventCreate, EventRead, EventUpdate
from src.event.services import create_event, delete_event, get_all_events, get_event, get_events_by_brand, apply_to_event, get_event_appplications
from src.database import get_session

router = APIRouter()

@router.post("/create_event{current_brand_id}", response_model=EventRead)
async def create_event_endpoint(event_in: EventCreate, current_brand_id: str, current_users: Users = Depends(get_current_user),db: AsyncSession = Depends(get_session)):  
    new_event = await create_event(current_users,current_brand_id, event_in, db)
    return new_event

@router.get("/eventsbybrand/{brand_id}", response_model= list[EventRead])
async def get_events_by_brand_endpoint( brand_id: str, db: AsyncSession = Depends(get_session)):
    events = await get_events_by_brand( brand_id, db)
    return events


@router.delete("/delete_event/{event_id}")
async def delete_event_endpoint( event_id: str, current_user: Users = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    await delete_event( current_user, event_id, db)


# event appplications endpoints will be here

@router.post ("/apply_event/{event_id}", response_model=EventApplicationRead)
async def apply_to_event_endpoint(event_id: str, application_in: EventApplicationCreate, current_user: Users = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    application = await apply_to_event(current_user, event_id, application_in, db)
    return application


