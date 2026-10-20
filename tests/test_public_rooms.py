import asyncio
import os
import time
from datetime import date, datetime
from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.api.v1 import public
from app.core.timezone import local_day_bounds_utc


class FakeRoomModel:
    room = None

    @classmethod
    async def get(cls, _object_id):
        return cls.room


class FakeBookingModel:
    start_time = "start_time"
    queries = []
    rows = []

    @classmethod
    def find(cls, query):
        cls.queries.append(query)
        rows = cls.rows
        return SimpleNamespace(sort=lambda _field: SimpleNamespace(to_list=_async_value(rows)))


def _async_value(value):
    async def to_list():
        return value
    return to_list


def _room(**overrides):
    data = dict(
        id=ObjectId(), name="Ruang A", capacity=8, facilities=["AC"], location="Lantai 2",
        is_active=True, created_at=datetime(2026, 1, 1), photo_updated_at=None,
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def _booking(title="Rapat", published=True, start=datetime(2026, 5, 4, 2, 0), end=datetime(2026, 5, 4, 3, 30)):
    return SimpleNamespace(
        title=title, published=published, start_time=start, end_time=end,
        user_snapshot=SimpleNamespace(division="Teknologi", full_name="Rahasia"),
        description="Rahasia", booking_number="BK-1",
    )


@pytest.fixture(autouse=True)
def models(monkeypatch):
    FakeRoomModel.room = _room()
    FakeBookingModel.queries = []
    FakeBookingModel.rows = []
    monkeypatch.setattr(public, "Room", FakeRoomModel)
    monkeypatch.setattr(public, "Booking", FakeBookingModel)


def test_room_details_are_returned_without_a_user():
    result = asyncio.run(public.get_public_room(str(FakeRoomModel.room.id)))

    assert result.name == "Ruang A"
    assert result.location == "Lantai 2"
    assert result.facilities == ["AC"]
    assert result.photo_url is None


@pytest.mark.parametrize("room_id", ["not-an-object-id", str(ObjectId())])
def test_unknown_or_malformed_room_is_404(room_id):
    FakeRoomModel.room = None

    with pytest.raises(HTTPException) as error:
        asyncio.run(public.get_public_room(room_id))

    assert error.value.status_code == 404


def test_inactive_room_is_404_not_revealed():
    FakeRoomModel.room = _room(is_active=False)

    with pytest.raises(HTTPException) as error:
        asyncio.run(public.get_public_room(str(FakeRoomModel.room.id)))

    assert error.value.status_code == 404


def test_schedule_exposes_only_time_title_and_division():
    FakeBookingModel.rows = [_booking()]

    slots = asyncio.run(public.get_public_room_schedule(str(FakeRoomModel.room.id), day=date(2026, 5, 4)))

    assert [slot.model_dump() for slot in slots] == [{
        "start_time": "2026-05-04T02:00:00Z",
        "end_time": "2026-05-04T03:30:00Z",
        "title": "Rapat",
        "division": "Teknologi",
    }]


def test_draft_keeps_its_slot_but_hides_the_title():
    FakeBookingModel.rows = [_booking(title="Rencana rahasia", published=False)]

    slots = asyncio.run(public.get_public_room_schedule(str(FakeRoomModel.room.id), day=date(2026, 5, 4)))

    assert slots[0].title == "Terisi"


def test_schedule_only_asks_for_active_bookings_of_that_room_and_day():
    asyncio.run(public.get_public_room_schedule(str(FakeRoomModel.room.id), day=date(2026, 5, 4)))

    query = FakeBookingModel.queries[0]
    assert query["room_id"] == FakeRoomModel.room.id
    assert query["status"] == "active"
    assert query["start_time"] == {"$lt": datetime(2026, 5, 4, 17, 0)}
    assert query["end_time"] == {"$gt": datetime(2026, 5, 3, 17, 0)}


@pytest.mark.parametrize("zone", ["UTC", "America/New_York", "Asia/Tokyo"])
def test_day_bounds_are_jakarta_whatever_the_server_zone(zone):
    original = os.environ.get("TZ")
    os.environ["TZ"] = zone
    time.tzset()
    try:
        start, end = local_day_bounds_utc(date(2026, 5, 4))
    finally:
        if original is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = original
        time.tzset()

    assert start == datetime(2026, 5, 3, 17, 0)
    assert end == datetime(2026, 5, 4, 17, 0)
