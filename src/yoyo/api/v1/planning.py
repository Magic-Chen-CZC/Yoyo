from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.api.deps import get_db_session
from yoyo.api.responses import success_response
from yoyo.modules.planner.recommendation_schemas import RecommendationRead, RecommendationRequest
from yoyo.modules.planner.recommendation_service import build_route_recommendations
from yoyo.modules.planner.schemas import CreateItineraryRequest, RouteEditRequest
from yoyo.modules.planner.service import (
    create_itinerary,
    edit_itinerary,
    get_itinerary,
    list_itinerary_versions,
)
from yoyo.modules.planner.template_repository import list_route_templates

router = APIRouter(prefix="/planning")


@router.get("/templates")
async def list_route_templates_endpoint() -> dict[str, object]:
    return success_response(list_route_templates())


@router.post("/recommendations")
async def create_route_recommendations_endpoint(
    payload: RecommendationRequest,
) -> dict[str, object]:
    recommendations = [
        RecommendationRead.model_validate(item).model_dump()
        for item in build_route_recommendations(payload.preferences)
    ]
    return success_response(recommendations)


@router.post("/itineraries", status_code=status.HTTP_201_CREATED)
async def create_itinerary_endpoint(
    payload: CreateItineraryRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> dict[str, object]:
    itinerary = await create_itinerary(session, payload)
    return success_response(itinerary.model_dump(), message="created")


@router.get("/itineraries/{itinerary_id}")
async def get_itinerary_endpoint(
    itinerary_id: str,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> dict[str, object]:
    itinerary = await get_itinerary(session, itinerary_id)
    if itinerary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="itinerary not found")

    return success_response(itinerary.model_dump())


@router.get("/itineraries/{itinerary_id}/versions")
async def list_itinerary_versions_endpoint(
    itinerary_id: str,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> dict[str, object]:
    versions = await list_itinerary_versions(session, itinerary_id)
    if versions is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="itinerary not found")

    return success_response([version.model_dump() for version in versions])


@router.post("/itineraries/{itinerary_id}/edits")
async def edit_itinerary_endpoint(
    itinerary_id: str,
    payload: RouteEditRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> dict[str, object]:
    try:
        itinerary = await edit_itinerary(session, itinerary_id, payload)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    if itinerary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="itinerary not found")

    return success_response(itinerary.model_dump())
