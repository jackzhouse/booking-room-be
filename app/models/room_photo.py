from datetime import datetime, timezone

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field


class RoomPhoto(Document):
    """Photo of a room, stored in MongoDB so it survives redeploys without a mounted volume."""
    room_id: Indexed(PydanticObjectId, unique=True)
    content_type: str
    data: bytes
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "room_photos"
