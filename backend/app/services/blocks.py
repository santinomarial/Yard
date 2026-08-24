import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.messaging import Block


async def interaction_is_blocked(
    session: AsyncSession, first_user_id: uuid.UUID, second_user_id: uuid.UUID
) -> bool:
    block = await session.scalar(
        select(Block.blocker_id).where(
            or_(
                (Block.blocker_id == first_user_id) & (Block.blocked_id == second_user_id),
                (Block.blocker_id == second_user_id) & (Block.blocked_id == first_user_id),
            )
        )
    )
    return block is not None
