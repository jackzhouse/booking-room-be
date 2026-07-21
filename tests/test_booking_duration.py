import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

from app.services import conflict_service


def test_validate_booking_duration_uses_default_minimum(monkeypatch):
    async def fake_get_min_booking_duration_minutes():
        return 15

    monkeypatch.setattr(conflict_service, "get_min_booking_duration_minutes", fake_get_min_booking_duration_minutes)

    start_time = datetime(2026, 7, 8, 7, 0, tzinfo=timezone.utc)
    end_time = datetime(2026, 7, 8, 7, 10, tzinfo=timezone.utc)

    is_valid, error_message = asyncio.run(conflict_service.validate_booking_duration(start_time, end_time))

    assert is_valid is False
    assert error_message == "Durasi minimal booking adalah 15 menit. Anda memilih 10 menit."


def test_validate_booking_duration_honors_custom_setting(monkeypatch):
    async def fake_get_min_booking_duration_minutes():
        return 30

    monkeypatch.setattr(conflict_service, "get_min_booking_duration_minutes", fake_get_min_booking_duration_minutes)

    start_time = datetime(2026, 7, 8, 7, 0, tzinfo=timezone.utc)
    end_time = datetime(2026, 7, 8, 7, 20, tzinfo=timezone.utc)

    is_valid, error_message = asyncio.run(conflict_service.validate_booking_duration(start_time, end_time))

    assert is_valid is False
    assert error_message == "Durasi minimal booking adalah 30 menit. Anda memilih 20 menit."


def test_validate_booking_duration_allows_admin_bypass():
    start_time = datetime(2026, 7, 8, 7, 0, tzinfo=timezone.utc)
    end_time = datetime(2026, 7, 8, 7, 5, tzinfo=timezone.utc)

    is_valid, error_message = asyncio.run(
        conflict_service.validate_booking_duration(start_time, end_time, is_admin=True)
    )

    assert is_valid is True
    assert error_message is None


def test_get_min_booking_duration_minutes_falls_back_on_invalid_value(monkeypatch):
    async def fake_find_one(_query):
        return SimpleNamespace(value="not-a-number")

    monkeypatch.setattr(conflict_service.Setting, "find_one", fake_find_one)

    result = asyncio.run(conflict_service.get_min_booking_duration_minutes())

    assert result == 15
