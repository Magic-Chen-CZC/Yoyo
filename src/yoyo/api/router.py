from fastapi import APIRouter

from yoyo.api.v1.gps import router as gps_router
from yoyo.api.v1.guide import router as guide_router
from yoyo.api.v1.health import router as health_router
from yoyo.api.v1.map import router as map_router
from yoyo.api.v1.planning import router as planning_router
from yoyo.api.v1.qa import router as qa_router
from yoyo.api.v1.questionnaire import router as questionnaire_router
from yoyo.api.v1.session import router as session_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(questionnaire_router, tags=["questionnaire"])
api_router.include_router(planning_router, tags=["planning"])
api_router.include_router(guide_router, tags=["guide"])
api_router.include_router(session_router, tags=["session"])
api_router.include_router(map_router, tags=["map"])
api_router.include_router(gps_router, tags=["gps"])
api_router.include_router(qa_router, tags=["qa"])
