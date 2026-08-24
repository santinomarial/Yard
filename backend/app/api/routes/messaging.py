import uuid
from collections import defaultdict
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from jwt import InvalidTokenError
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionFactory, get_session
from app.core.security import CurrentUser, decode_access_token
from app.models.listing import Listing
from app.models.messaging import Block, Conversation, ConversationMember, Message
from app.models.user import User
from app.schemas.messaging import (
    ConversationCreate,
    ConversationRead,
    MessageCreate,
    MessageRead,
)
from app.services.messaging import MessagingError, member_ids, persist_message, require_member

router = APIRouter()


def messaging_error(error: MessagingError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN
        if error.code == "interaction_blocked"
        else status.HTTP_404_NOT_FOUND,
        detail={"code": error.code, "message": str(error)},
    )


async def conversation_read(session: AsyncSession, conversation: Conversation) -> ConversationRead:
    return ConversationRead(
        id=conversation.id,
        listing_id=conversation.listing_id,
        member_ids=await member_ids(session, conversation.id),
        updated_at=conversation.updated_at,
    )


@router.post("/conversations", response_model=ConversationRead, status_code=201)
async def create_conversation(
    payload: ConversationCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ConversationRead:
    listing = await session.get(Listing, payload.listing_id)
    if listing is None or listing.seller_id == user.id:
        raise HTTPException(status_code=404, detail="Not found")
    existing = await session.scalar(
        select(Conversation).where(
            Conversation.listing_id == listing.id,
            Conversation.buyer_id == user.id,
        )
    )
    if existing:
        return await conversation_read(session, existing)
    conversation = Conversation(id=uuid.uuid4(), listing_id=listing.id, buyer_id=user.id)
    session.add(conversation)
    session.add_all(
        [
            ConversationMember(conversation_id=conversation.id, user_id=user.id),
            ConversationMember(conversation_id=conversation.id, user_id=listing.seller_id),
        ]
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        recovered = await session.scalar(
            select(Conversation).where(
                Conversation.listing_id == listing.id,
                Conversation.buyer_id == user.id,
            )
        )
        if recovered is None:
            raise
        conversation = recovered
    return await conversation_read(session, conversation)


@router.get("/conversations", response_model=list[ConversationRead])
async def conversations(
    user: CurrentUser, session: AsyncSession = Depends(get_session)
) -> list[ConversationRead]:
    rows = await session.scalars(
        select(Conversation)
        .join(ConversationMember)
        .where(ConversationMember.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
    )
    return [await conversation_read(session, item) for item in rows.unique().all()]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageRead])
async def messages(
    conversation_id: uuid.UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> list[Message]:
    try:
        await require_member(session, conversation_id, user.id)
    except MessagingError as error:
        raise messaging_error(error) from None
    rows = await session.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at, Message.id)
        .limit(200)
    )
    return list(rows.all())


@router.post("/conversations/{conversation_id}/messages", response_model=MessageRead)
async def send_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> Message:
    try:
        message = await persist_message(session, conversation_id, user.id, payload.body)
    except MessagingError as error:
        raise messaging_error(error) from None
    await sockets.broadcast(
        conversation_id, MessageRead.model_validate(message).model_dump(mode="json")
    )
    return message


@router.post("/conversations/{conversation_id}/read", status_code=204)
async def mark_conversation_read(
    conversation_id: uuid.UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> None:
    member = await session.get(ConversationMember, (conversation_id, user.id))
    if member is None:
        raise HTTPException(status_code=404, detail="Not found")
    member.last_read_at = datetime.now(UTC)
    await session.commit()


@router.put("/blocks/{blocked_id}", status_code=204)
async def block_user(
    blocked_id: uuid.UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> None:
    if blocked_id == user.id or await session.get(User, blocked_id) is None:
        raise HTTPException(status_code=404, detail="Not found")
    if await session.get(Block, (user.id, blocked_id)) is None:
        session.add(Block(blocker_id=user.id, blocked_id=blocked_id))
        await session.commit()


class SocketHub:
    def __init__(self) -> None:
        self.connections: dict[uuid.UUID, set[WebSocket]] = defaultdict(set)

    async def connect(self, conversation_id: uuid.UUID, socket: WebSocket) -> None:
        await socket.accept()
        self.connections[conversation_id].add(socket)

    def disconnect(self, conversation_id: uuid.UUID, socket: WebSocket) -> None:
        self.connections[conversation_id].discard(socket)

    async def broadcast(self, conversation_id: uuid.UUID, payload: dict[str, object]) -> None:
        failed: list[WebSocket] = []
        for socket in self.connections[conversation_id]:
            try:
                await socket.send_json(payload)
            except RuntimeError:
                failed.append(socket)
        for socket in failed:
            self.disconnect(conversation_id, socket)


sockets = SocketHub()


@router.websocket("/conversations/{conversation_id}/ws")
async def conversation_socket(websocket: WebSocket, conversation_id: uuid.UUID) -> None:
    authorization = websocket.headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        await websocket.close(code=4401)
        return
    try:
        user_id = decode_access_token(authorization.removeprefix("Bearer "))
        async with SessionFactory() as session:
            user = await session.get(User, user_id)
            if user is None:
                raise ValueError
            await require_member(session, conversation_id, user_id)
    except (InvalidTokenError, KeyError, ValueError, MessagingError):
        await websocket.close(code=4403)
        return
    await sockets.connect(conversation_id, websocket)
    try:
        while True:
            payload = MessageCreate.model_validate_json(await websocket.receive_text())
            async with SessionFactory() as session:
                message = await persist_message(session, conversation_id, user_id, payload.body)
            await sockets.broadcast(
                conversation_id, MessageRead.model_validate(message).model_dump(mode="json")
            )
    except (WebSocketDisconnect, ValidationError, MessagingError):
        sockets.disconnect(conversation_id, websocket)
