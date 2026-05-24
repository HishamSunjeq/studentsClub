from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatSessionResponse(BaseModel):
    id: UUID
    subject_id: UUID
    title: str
    last_message_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionListResponse(BaseModel):
    items: list[ChatSessionResponse]


class ChatCitation(BaseModel):
    chunk_id: UUID
    upload_id: UUID | None = None
    section_title: str | None = None
    text: str


class ChatMessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    citations: list[ChatCitation] = Field(default_factory=list)
    model: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageListResponse(BaseModel):
    items: list[ChatMessageResponse]


class ChatSessionCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class ChatSendRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class ChatSendResponse(BaseModel):
    """The persisted user turn plus the grounded assistant reply."""

    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
