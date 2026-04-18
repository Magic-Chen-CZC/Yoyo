from pydantic import BaseModel


class CommentCreateRequest(BaseModel):
    user_id: str
    content: str
    guide_session_id: str | None = None


class CommentRead(BaseModel):
    id: str
    stop_id: str
    user_id: str
    content: str
    status: str
    guide_session_id: str | None = None
    created_at: str
