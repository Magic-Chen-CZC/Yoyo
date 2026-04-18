from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.db.models.guest import GuestUser
from yoyo.modules.guest.schemas import GuestSessionCreateResponse


async def create_guest_session(session: AsyncSession) -> GuestSessionCreateResponse:
    guest_user = GuestUser()
    session.add(guest_user)
    await session.commit()
    await session.refresh(guest_user)
    return GuestSessionCreateResponse(
        guest_user_id=guest_user.id,
        anonymous_token=guest_user.anonymous_token,
        status=guest_user.status,
    )
