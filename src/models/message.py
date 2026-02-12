from datetime import datetime

from pydantic import BaseModel


class MessageDTO(BaseModel):
    """Data transfer object for messages."""

    message_id: int
    chat_id: int
    user_id: int
    username: str | None = None
    text: str | None = None
    reply_to_message_id: int | None = None
    timestamp: datetime

    class Config:
        from_attributes = True
