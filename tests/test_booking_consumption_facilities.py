import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import create_autospec

import pytest
from bson import ObjectId

from app.services import booking_service, telegram_service
from tests.test_booking_notifications import (
    FakeBooking,
    FakeCreatedBooking,
    FixedDateTime,
    _install_common_mocks,
)

CONSUMPTION_GROUP = -5181257488


def _update(booking, **kwargs):
    return asyncio.run(
        booking_service.update_booking(booking_id=str(booking.id), user_id=booking.user_id, **kwargs)
    )


def _spy_consumption(monkeypatch):
    sent = {"update": [], "cancelled": []}

    async def fake_update(booking, is_update=False, message_ref=None):
        sent["update"].append(is_update)

    async def fake_cancelled(booking, chat_id=None):
        sent["cancelled"].append(chat_id)

    monkeypatch.setattr(booking_service, "notify_consumption_group", fake_update)
    monkeypatch.setattr(booking_service, "notify_consumption_group_cancelled", fake_cancelled)
    return sent


def test_create_with_facilities_and_unticked_consumption_stays_unticked_but_reaches_the_group(monkeypatch):
    async def fake_room_get(_room_id):
        return SimpleNamespace(name="Kantin", is_active=True, facilities=["AC", "Proyektor"])

    async def fake_user_get(_user_id):
        return SimpleNamespace(
            full_name="SYIFA", username="syifa", division="IT", telegram_id=None,
            telegram_username=None, external_user_id="x",
        )

    async def fake_group(_group_id):
        return SimpleNamespace(is_active=True)

    async def fake_valid(*args, **kwargs):
        return True, None

    async def fake_conflict(*args, **kwargs):
        return False, None

    class FakeSetting:
        key = "key"

        @staticmethod
        async def find_one(_query):
            return SimpleNamespace(value=str(CONSUMPTION_GROUP))

    async def fake_history(*args, **kwargs):
        return None

    async def fake_number():
        return "BK-09998"

    monkeypatch.setattr(booking_service.Room, "get", fake_room_get)
    monkeypatch.setattr(booking_service.User, "get", fake_user_get)
    monkeypatch.setattr(booking_service, "get_telegram_group", fake_group)
    monkeypatch.setattr(booking_service, "validate_operating_hours", fake_valid)
    monkeypatch.setattr(booking_service, "validate_booking_duration", fake_valid)
    monkeypatch.setattr(booking_service, "check_booking_conflict", fake_conflict)
    monkeypatch.setattr(booking_service, "Setting", FakeSetting)
    monkeypatch.setattr(booking_service, "create_history", fake_history)
    monkeypatch.setattr(booking_service, "generate_booking_number", fake_number)
    monkeypatch.setattr(booking_service, "Booking", FakeCreatedBooking)
    monkeypatch.setattr(booking_service, "datetime", FixedDateTime)

    result = asyncio.run(
        booking_service.create_booking(
            user_id=ObjectId(),
            room_id=str(ObjectId()),
            telegram_group_id=-1001111111111,
            title="Rapat",
            start_time=datetime(2026, 7, 8, 11, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc),
            has_consumption=False,
            consumption_facilities=["AC"],
        )
    )

    assert result.has_consumption is False
    assert result.consumption_facilities == ["AC"]
    assert result.consumption_group_id == CONSUMPTION_GROUP  # the default group is filled for facilities too


def test_publish_sends_facilities_only_booking_to_the_consumption_group(monkeypatch):
    booking = FakeBooking(published=False, has_consumption=False)
    _install_common_mocks(monkeypatch, booking, [])
    posted: list[str] = []

    async def fake_main(*args, **kwargs):
        return None

    async def fake_consumption(*args, **kwargs):
        posted.append("consumption")

    monkeypatch.setattr(booking_service, "notify_new_booking", fake_main)
    monkeypatch.setattr(booking_service, "notify_verification_group_booking", fake_main)
    monkeypatch.setattr(booking_service, "notify_consumption_group", fake_consumption)
    monkeypatch.setattr(booking_service, "datetime", FixedDateTime)

    asyncio.run(booking_service.publish_booking(str(booking.id), booking.user_id))

    assert posted == ["consumption"]


def test_publish_skips_consumption_group_when_neither_consumption_nor_facilities(monkeypatch):
    booking = FakeBooking(published=False, has_consumption=False)
    booking.consumption_facilities = []
    _install_common_mocks(monkeypatch, booking, [])
    posted: list[str] = []

    async def fake_main(*args, **kwargs):
        return None

    async def fake_consumption(*args, **kwargs):
        posted.append("consumption")

    monkeypatch.setattr(booking_service, "notify_new_booking", fake_main)
    monkeypatch.setattr(booking_service, "notify_verification_group_booking", fake_main)
    monkeypatch.setattr(booking_service, "notify_consumption_group", fake_consumption)
    monkeypatch.setattr(booking_service, "datetime", FixedDateTime)

    asyncio.run(booking_service.publish_booking(str(booking.id), booking.user_id))

    assert posted == []


def test_unticking_consumption_keeps_facilities_and_updates_the_group(monkeypatch):
    booking = FakeBooking(published=True, has_consumption=True)
    _install_common_mocks(monkeypatch, booking, [])
    sent = _spy_consumption(monkeypatch)

    result = _update(booking, has_consumption=False, consumption_facilities=["AC", "Proyektor"])

    assert result.has_consumption is False
    assert result.consumption_facilities == ["AC", "Proyektor"]
    assert sent == {"update": [True], "cancelled": []}


def test_clearing_consumption_and_facilities_cancels_the_group_request(monkeypatch):
    booking = FakeBooking(published=True, has_consumption=True)
    _install_common_mocks(monkeypatch, booking, [])
    sent = _spy_consumption(monkeypatch)

    result = _update(booking, has_consumption=False, consumption_facilities=[])

    assert result.has_consumption is False
    assert sent["cancelled"] == [CONSUMPTION_GROUP]
    assert sent["update"] == []


def test_clearing_only_facilities_keeps_consumption_active(monkeypatch):
    booking = FakeBooking(published=True, has_consumption=True)
    _install_common_mocks(monkeypatch, booking, [])
    sent = _spy_consumption(monkeypatch)

    result = _update(booking, has_consumption=True, consumption_facilities=[])

    assert result.has_consumption is True
    assert sent == {"update": [True], "cancelled": []}


def test_update_without_has_consumption_keeps_the_current_choice(monkeypatch):
    booking = FakeBooking(published=False, has_consumption=False)
    _install_common_mocks(monkeypatch, booking, [])

    result = _update(booking, title="Judul Baru")

    assert result.has_consumption is False


def test_cancel_notifies_consumption_group_for_facilities_only_booking(monkeypatch):
    booking = FakeBooking(published=True, has_consumption=False)
    _install_common_mocks(monkeypatch, booking, [])
    sent = _spy_consumption(monkeypatch)

    async def fake_cancel(*args, **kwargs):
        return None

    monkeypatch.setattr(booking_service, "notify_booking_cancelled", fake_cancel)
    monkeypatch.setattr(booking_service, "notify_verification_group_cancelled", fake_cancel)

    asyncio.run(booking_service.cancel_booking(str(booking.id), booking.user_id))

    assert sent["cancelled"] == [None]


def test_consumption_message_lists_only_what_is_active():
    facilities_only = FakeBooking(has_consumption=False)
    both = FakeBooking(has_consumption=True)
    note_only = FakeBooking(has_consumption=True)
    note_only.consumption_facilities = []

    only_facilities_text = telegram_service._render_series_notification([facilities_only], "consumption", "new")
    both_text = telegram_service._render_series_notification([both], "consumption", "new")
    note_text = telegram_service._render_series_notification([note_only], "consumption", "new")

    assert "• AC" in only_facilities_text and "Konsumsi:" not in only_facilities_text
    assert "• AC" in both_text and "Konsumsi:" in both_text and "• test" in both_text
    assert "Fasilitas:" not in note_text and "• test" in note_text


def test_completion_targets_include_consumption_for_facilities_only_but_not_for_nothing():
    facilities_only = FakeBooking(has_consumption=False)
    nothing = FakeBooking(has_consumption=False)
    nothing.consumption_facilities = []

    assert "consumption" in telegram_service.completion_targets(facilities_only)
    assert "consumption" not in telegram_service.completion_targets(nothing)
