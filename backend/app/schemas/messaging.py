import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.messaging import MessageType


class ConversationCreate(BaseModel):
    listing_id: uuid.UUID


class ConversationRead(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    member_ids: list[uuid.UUID]
    updated_at: datetime


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2_000)


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID | None
    message_type: MessageType
    body: str
    created_at: datetime
