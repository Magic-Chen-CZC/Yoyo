from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.db.models.comment import POIComment
from yoyo.modules.comments.schemas import CommentCreateRequest, CommentRead


async def create_comment(
    session: AsyncSession,
    stop_id: str,
    payload: CommentCreateRequest,
) -> CommentRead:
    comment = POIComment(
        stop_id=stop_id,
        user_id=payload.user_id,
        guide_session_id=payload.guide_session_id,
        content=payload.content,
        status="visible",
    )
    session.add(comment)
    await session.commit()
    await session.refresh(comment)
    return _serialize_comment(comment)


async def list_comments_for_stop(session: AsyncSession, stop_id: str) -> list[CommentRead]:
    result = await session.execute(
        select(POIComment)
        .where(POIComment.stop_id == stop_id)
        .where(POIComment.status == "visible")
        .order_by(POIComment.created_at.desc())
    )
    return [_serialize_comment(item) for item in result.scalars().all()]


async def summarize_comments_by_stop_ids(
    session: AsyncSession,
    stop_ids: list[str],
) -> dict[str, dict[str, object]]:
    summary = {
        stop_id: {"comment_count": 0, "latest_comment_preview": None}
        for stop_id in stop_ids
    }
    if not stop_ids:
        return summary

    result = await session.execute(
        select(POIComment)
        .where(POIComment.stop_id.in_(stop_ids))
        .where(POIComment.status == "visible")
        .order_by(POIComment.created_at.desc())
    )
    for item in result.scalars().all():
        row = summary.setdefault(
            item.stop_id,
            {"comment_count": 0, "latest_comment_preview": None},
        )
        row["comment_count"] = int(row["comment_count"]) + 1
        if row["latest_comment_preview"] is None:
            row["latest_comment_preview"] = item.content[:80]
    return summary



def _serialize_comment(comment: POIComment) -> CommentRead:
    return CommentRead(
        id=comment.id,
        stop_id=comment.stop_id,
        user_id=comment.user_id,
        content=comment.content,
        status=comment.status,
        guide_session_id=comment.guide_session_id,
        created_at=comment.created_at.isoformat(),
    )
