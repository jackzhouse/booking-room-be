import asyncio
import os
import time
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.core.timezone import to_local
from app.services import conflict_service


@pytest.fixture(params=["UTC", "America/New_York", "Asia/Tokyo"])
def server_tz(request):
    previous = os.environ.get("TZ")
    os.environ["TZ"] = request.param
    time.tzset()
    yield request.param
    if previous is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = previous
    time.tzset()


def test_to_local_reads_naive_datetime_as_utc(server_tz):
    assert to_local(datetime(2026, 10, 16, 7, 0)).strftime("%H:%M") == "14:00"


def test_to_local_converts_aware_datetime(server_tz):
    aware = datetime(2026, 10, 16, 7, 0, tzinfo=timezone.utc)
    assert to_local(aware).strftime("%H:%M") == "14:00"


def test_conflict_message_uses_wib_regardless_of_server_timezone(server_tz):
    conflicting = SimpleNamespace(
        user_snapshot=SimpleNamespace(full_name="Syifa", division="IT"),
        room_snapshot=SimpleNamespace(name="Ruang A"),
        start_time=datetime(2026, 10, 16, 7, 0),
        end_time=datetime(2026, 10, 16, 8, 30),
    )

    message = asyncio.run(conflict_service.format_conflict_message(conflicting))

    assert message == "Ruangan sudah dibooking oleh Syifa (IT) pukul 14:00–15:30 WIB di Ruang A"


def test_operating_hours_message_uses_wib_regardless_of_server_timezone(server_tz, monkeypatch):
    async def fake_hours():
        return datetime(2000, 1, 1, 8, 0).time(), datetime(2000, 1, 1, 18, 0).time()

    monkeypatch.setattr(conflict_service, "get_operating_hours", fake_hours)

    # 12:00-13:00 UTC is 19:00-20:00 WIB, outside 08:00-18:00.
    valid, message = asyncio.run(
        conflict_service.validate_operating_hours(
            datetime(2026, 10, 16, 12, 0), datetime(2026, 10, 16, 13, 0)
        )
    )

    assert valid is False
    assert "Booking Anda: 19:00 - 20:00" in message
