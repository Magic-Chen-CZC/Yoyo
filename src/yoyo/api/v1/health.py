from fastapi import APIRouter

from yoyo.api.responses import success_response

router = APIRouter()


@router.get("/health")
async def healthcheck() -> dict[str, object]:
    return success_response({"status": "ok"}, message="ok")
