import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.messaging import Conversation, ConversationMember, Message, MessageType
from app.services.blocks import interaction_is_blocked


class MessagingError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


async def member_ids(session: AsyncSession, conversation_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        (
            await session.scalars(
                select(ConversationMember.user_id).where(
                    ConversationMember.conversation_id == conversation_id
                )
            )
        ).all()
    )


async def require_member(
    session: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID
) -> list[uuid.UUID]:
    members = await member_ids(session, conversation_id)
    if user_id not in members:
        raise MessagingError("conversation_not_found", "This conversation is unavailable.")
    return members


async def ensure_not_blocked(
    session: AsyncSession, sender_id: uuid.UUID, members: list[uuid.UUID]
) -> None:
    peers = [member for member in members if member != sender_id]
    if not peers:
        raise MessagingError("conversation_invalid", "This conversation has no recipient.")
    if any(
        [await interaction_is_blocked(session, sender_id, peer) for peer in peers]
    ):
        raise MessagingError("interaction_blocked", "Messaging is unavailable.")


async def persist_message(
    session: AsyncSession, conversation_id: uuid.UUID, sender_id: uuid.UUID, body: str
) -> Message:
    normalized = body.strip()
    if not normalized or len(normalized) > 2_000:
        raise MessagingError("invalid_message", "Messages must be 1 to 2,000 characters.")
    members = await require_member(session, conversation_id, sender_id)
    await ensure_not_blocked(session, sender_id, members)
    message = Message(
        id=uuid.uuid4(),
        conversation_id=conversation_id,
        sender_id=sender_id,
        message_type=MessageType.TEXT,
        body=normalized,
    )
    session.add(message)
    conversation = await session.get(Conversation, conversation_id)
    if conversation:
        conversation.updated_at = datetime.now(UTC)
    await session.commit()
    return message
