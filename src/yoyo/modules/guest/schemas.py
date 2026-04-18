from pydantic import BaseModel


class GuestSessionCreateResponse(BaseModel):
    guest_user_id: str
    anonymous_token: str
    status: str
