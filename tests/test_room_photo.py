import asyncio
import io
from datetime import datetime
from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi import HTTPException, UploadFile

from app.api.v1 import rooms
from app.schemas.room import room_to_response

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 32


def _upload(data: bytes) -> UploadFile:
    return UploadFile(file=io.BytesIO(data), filename="ruang.jpg")


class FakeRoom(SimpleNamespace):
    async def save(self):
        return None


class FakePhoto:
    """Stand-in for the Beanie RoomPhoto document."""
    room_id = None
    stored: dict = {}
    deleted: list = []

    def __init__(self, room_id, content_type, data, updated_at):
        self.room_id, self.content_type, self.data, self.updated_at = room_id, content_type, data, updated_at

    async def insert(self):
        FakePhoto.stored[self.room_id] = self

    async def save(self):
        return None

    @classmethod
    async def find_one(cls, _expr):
        return next(iter(cls.stored.values()), None)

    @classmethod
    def find(cls, _expr):
        return SimpleNamespace(delete=cls._delete)

    @staticmethod
    async def _delete():
        FakePhoto.stored.clear()
        FakePhoto.deleted.append(True)


@pytest.fixture
def room(monkeypatch):
    fake_room = FakeRoom(
        id=ObjectId(), name="Ruang A", capacity=8, facilities=["AC"], location=None,
        is_active=True, created_at=datetime(2026, 1, 1), photo_updated_at=None,
    )

    async def fake_get_room(_room_id):
        return fake_room

    FakePhoto.stored = {}
    FakePhoto.deleted = []
    FakePhoto.room_id = SimpleNamespace(__eq__=lambda *_: True)
    monkeypatch.setattr(rooms, "_get_room_or_404", fake_get_room)
    monkeypatch.setattr(rooms, "RoomPhoto", FakePhoto)
    return fake_room


@pytest.mark.parametrize("data,expected", [
    (JPEG, "image/jpeg"),
    (PNG, "image/png"),
    (WEBP, "image/webp"),
    (b"GIF89a" + b"\x00" * 32, None),
    (b"<svg></svg>", None),
    (b"", None),
])
def test_detect_image_type_uses_file_bytes(data, expected):
    assert rooms._detect_image_type(data) == expected


def test_upload_stores_photo_and_returns_versioned_url(room):
    response = asyncio.run(rooms.upload_room_photo(str(room.id), _upload(PNG), current_user=None))

    assert room.photo_updated_at is not None
    assert response.photo_url == f"/api/v1/rooms/{room.id}/photo?v={int(room.photo_updated_at.timestamp())}"
    stored = next(iter(FakePhoto.stored.values()))
    assert (stored.content_type, stored.data) == ("image/png", PNG)


def test_upload_rejects_non_image_even_with_image_filename(room):
    with pytest.raises(HTTPException) as error:
        asyncio.run(rooms.upload_room_photo(str(room.id), _upload(b"<svg onload=x>"), current_user=None))

    assert error.value.status_code == 415
    assert room.photo_updated_at is None


def test_upload_rejects_photo_over_2_mb(room):
    too_big = JPEG + b"\x00" * rooms.MAX_PHOTO_BYTES

    with pytest.raises(HTTPException) as error:
        asyncio.run(rooms.upload_room_photo(str(room.id), _upload(too_big), current_user=None))

    assert error.value.status_code == 413
    assert FakePhoto.stored == {}


def test_delete_photo_clears_url(room):
    asyncio.run(rooms.upload_room_photo(str(room.id), _upload(JPEG), current_user=None))

    response = asyncio.run(rooms.delete_room_photo(str(room.id), current_user=None))

    assert room.photo_updated_at is None
    assert response.photo_url is None
    assert FakePhoto.deleted == [True]


def test_room_without_photo_has_no_photo_url(room):
    assert room_to_response(room).photo_url is None
