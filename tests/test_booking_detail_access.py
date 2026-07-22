from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from bson import ObjectId

from app.api.v1 import bookings


class FakeBooking:
    def __init__(self, booking_id, user_id):
        self.user_id = user_id
        self._data = {
            "_id": booking_id,
            "booking_number": "BK-001",
            "user_id": user_id,
            "user_snapshot": {"full_name": "Booking Owner"},
            "room_id": ObjectId(),
            "room_snapshot": {"name": "Ruang Rapat"},
            "telegram_group_id": 1,
            "title": "Lintas user",
            "start_time": datetime(2026, 7, 22, 9, tzinfo=timezone.utc),
            "end_time": datetime(2026, 7, 22, 10, tzinfo=timezone.utc),
            "status": "active",
            "published": True,
            "created_at": datetime(2026, 7, 21, tzinfo=timezone.utc),
            "updated_at": datetime(2026, 7, 21, tzinfo=timezone.utc),
        }

    def model_dump(self, by_alias=True):
        return self._data


@pytest.mark.asyncio
async def test_authenticated_non_owner_can_read_booking_detail(monkeypatch):
    booking_id = ObjectId()
    booking = FakeBooking(booking_id=booking_id, user_id=ObjectId())

    async def fake_get(received_id):
        assert received_id == booking_id
        return booking

    monkeypatch.setattr(bookings.Booking, "get", fake_get)

    response = await bookings.get_booking(
        str(booking_id),
        current_user=SimpleNamespace(id=ObjectId(), is_admin=False),
    )

    assert response.id == str(booking_id)
    assert response.user_snapshot.full_name == "Booking Owner"
