from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.api.deps import get_db_session
from yoyo.api.responses import success_response
from yoyo.modules.comments.schemas import CommentCreateRequest
from yoyo.modules.comments.service import create_comment, list_comments_for_stop

router = APIRouter(prefix="/comments")


@router.get("/stops/{stop_id}")
async def list_stop_comments(
    stop_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    comments = await list_comments_for_stop(session, stop_id)
    return success_response([item.model_dump() for item in comments])


@router.post("/stops/{stop_id}")
async def create_stop_comment(
    stop_id: str,
    payload: CommentCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    comment = await create_comment(session, stop_id, payload)
    return success_response(comment.model_dump(), message="created")
