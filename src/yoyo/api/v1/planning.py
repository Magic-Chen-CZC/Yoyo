from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.api.deps import get_db_session
from yoyo.api.responses import success_response
from yoyo.modules.planner.schemas import CreateItineraryRequest
from yoyo.modules.planner.service import create_itinerary, get_itinerary

router = APIRouter(prefix="/planning")


@router.post("/itineraries", status_code=status.HTTP_201_CREATED)
async def create_itinerary_endpoint(
    payload: CreateItineraryRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    itinerary = await create_itinerary(session, payload)
    return success_response(itinerary.model_dump(), message="created")


@router.get("/itineraries/{itinerary_id}")
async def get_itinerary_endpoint(
    itinerary_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    itinerary = await get_itinerary(session, itinerary_id)
    if itinerary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="itinerary not found")

    return success_response(itinerary.model_dump())
