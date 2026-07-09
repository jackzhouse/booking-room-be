import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from bson import ObjectId

from app.services import booking_service


class FakeBooking:
    def __init__(
        self,
        *,
        published: bool = True,
        has_consumption: bool = True,
        telegram_group_id: int = -1003952786718,
        verification_group_id: int = -4881064745,
        consumption_group_id: int = -5181257488,
    ):
        self.id = ObjectId()
        self.booking_number = "BK-00061"
        self.user_id = ObjectId()
        self.user_snapshot = SimpleNamespace(
            full_name="SYIFA MAULIDA",
            username="syifa.maulida",
            division="IT",
            telegram_id=None,
            telegram_username=None,
            external_user_id="67441c735dc2895b9a48782b",
        )
        self.room_id = ObjectId()
        self.room_snapshot = SimpleNamespace(name="Kantin")
        self.telegram_group_id = telegram_group_id
        self.title = "Test Joko"
        self.division = "IT"
        self.description = "Tests"
        self.start_time = datetime(2026, 7, 8, 7, 0, tzinfo=timezone.utc)
        self.end_time = datetime(2026, 7, 8, 7, 19, tzinfo=timezone.utc)
        self.status = "active"
        self.published = published
        self.cancelled_at = None
        self.cancelled_by = None
        self.has_consumption = has_consumption
        self.consumption_note = "test"
        self.consumption_group_id = consumption_group_id
        self.verification_group_id = verification_group_id
        self.hrd_notified = False
        self.updated_at = datetime(2026, 7, 8, 6, 50, tzinfo=timezone.utc)

    async def save(self):
        return None


class FakeCreatedBooking:
    def __init__(self, **kwargs):
        self.id = ObjectId()
        for key, value in kwargs.items():
            setattr(self, key, value)

    async def insert(self):
        return None


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        current = cls(2026, 7, 8, 10, 0, tzinfo=timezone.utc)
        return current if tz is None else current.astimezone(tz)


def _install_common_mocks(monkeypatch, booking: FakeBooking, calls: list[str]):
    async def fake_booking_get(_booking_id):
        return booking

    async def fake_user_get(_user_id):
        return SimpleNamespace(is_admin=False)

    async def fake_get_group(_group_id):
        return SimpleNamespace(is_active=True)

    async def fake_find_one(_query):
        return SimpleNamespace(value="-5181257488")

    async def fake_create_history(*args, **kwargs):
        return None

    monkeypatch.setattr(booking_service.Booking, "get", fake_booking_get)
    monkeypatch.setattr(booking_service.User, "get", fake_user_get)
    monkeypatch.setattr(booking_service, "get_telegram_group", fake_get_group)
    monkeypatch.setattr(booking_service.Setting, "find_one", fake_find_one)
    monkeypatch.setattr(booking_service, "create_history", fake_create_history)


def test_update_booking_notifies_only_relevant_targets(monkeypatch):
    booking = FakeBooking(published=True)
    calls: list[str] = []
    _install_common_mocks(monkeypatch, booking, calls)

    payloads: list[tuple[str, list[str]]] = []

    async def fake_notify_booking_updated(*args, **kwargs):
        target = "verification" if kwargs.get("chat_id") else "main"
        payloads.append((target, kwargs.get("changed_fields", [])))
        calls.append(target)

    async def fake_notify_booking_target_removed(*args, **kwargs):
        calls.append("target_removed")

    async def fake_notify_consumption_group(*args, **kwargs):
        calls.append("consumption")

    monkeypatch.setattr(booking_service, "notify_booking_updated", fake_notify_booking_updated)
    monkeypatch.setattr(booking_service, "notify_booking_target_removed", fake_notify_booking_target_removed)
    monkeypatch.setattr(booking_service, "notify_consumption_group", fake_notify_consumption_group)

    user_id = booking.user_id
    result = asyncio.run(
        booking_service.update_booking(
            booking_id=str(booking.id),
            user_id=user_id,
            telegram_group_id=-1001111111111,
            title="Updated Title",
            has_consumption=True,
            consumption_note="Updated note",
            consumption_group_id=-5181257488,
            verification_group_id=-4999999999,
        )
    )

    assert result.telegram_group_id == -1001111111111
    assert result.title == "Updated Title"
    assert result.consumption_note == "Updated note"
    assert calls == ["main", "verification", "consumption", "target_removed", "target_removed"]
    assert payloads == [
        ("main", ["judul", "grup utama"]),
        ("verification", ["judul", "grup utama", "grup verifikasi"]),
    ]


def test_update_booking_adds_consumption_using_default_group(monkeypatch):
    booking = FakeBooking(published=True, has_consumption=False, consumption_group_id=None)
    calls: list[str] = []
    _install_common_mocks(monkeypatch, booking, calls)

    async def fake_notify_booking_updated(*args, **kwargs):
        calls.append("verification" if kwargs.get("chat_id") else "main")

    async def fake_notify_consumption_group(*args, **kwargs):
        calls.append("consumption")

    monkeypatch.setattr(booking_service, "notify_booking_updated", fake_notify_booking_updated)
    monkeypatch.setattr(booking_service, "notify_consumption_group", fake_notify_consumption_group)

    result = asyncio.run(
        booking_service.update_booking(
            booking_id=str(booking.id),
            user_id=booking.user_id,
            has_consumption=True,
            consumption_note="New consumption",
        )
    )

    assert result.has_consumption is True
    assert result.consumption_group_id == -5181257488
    assert calls == ["consumption"]


def test_update_booking_draft_skips_notifications(monkeypatch):
    booking = FakeBooking(published=False)
    calls: list[str] = []
    _install_common_mocks(monkeypatch, booking, calls)

    async def fake_notify_booking_updated(*args, **kwargs):
        calls.append("verification" if kwargs.get("chat_id") else "main")

    async def fake_notify_verification_group_booking(*args, **kwargs):
        calls.append("verification")

    async def fake_notify_consumption_group(*args, **kwargs):
        calls.append("consumption")

    async def fake_notify_booking_target_removed(*args, **kwargs):
        calls.append("target_removed")

    monkeypatch.setattr(booking_service, "notify_booking_updated", fake_notify_booking_updated)
    monkeypatch.setattr(booking_service, "notify_consumption_group", fake_notify_consumption_group)
    monkeypatch.setattr(booking_service, "notify_booking_target_removed", fake_notify_booking_target_removed)

    asyncio.run(
        booking_service.update_booking(
            booking_id=str(booking.id),
            user_id=booking.user_id,
            title="Updated Title",
        )
    )

    assert calls == []


def test_cancel_booking_notifies_all_relevant_groups(monkeypatch):
    booking = FakeBooking(published=True)
    calls: list[str] = []
    _install_common_mocks(monkeypatch, booking, calls)

    async def fake_notify_booking_cancelled(*args, **kwargs):
        calls.append("main")

    async def fake_notify_verification_group_cancelled(*args, **kwargs):
        calls.append("verification")

    async def fake_notify_consumption_group_cancelled(*args, **kwargs):
        calls.append("consumption")

    monkeypatch.setattr(booking_service, "notify_booking_cancelled", fake_notify_booking_cancelled)
    monkeypatch.setattr(booking_service, "notify_verification_group_cancelled", fake_notify_verification_group_cancelled)
    monkeypatch.setattr(booking_service, "notify_consumption_group_cancelled", fake_notify_consumption_group_cancelled)

    result = asyncio.run(
        booking_service.cancel_booking(
            booking_id=str(booking.id),
            user_id=booking.user_id,
        )
    )

    assert result.status == "cancelled"
    assert result.cancelled_by == booking.user_id
    assert calls == ["main", "verification", "consumption"]


def test_update_booking_disabling_consumption_notifies_cancel(monkeypatch):
    booking = FakeBooking(published=True, has_consumption=True, consumption_group_id=-5181257488)
    calls: list[str] = []
    _install_common_mocks(monkeypatch, booking, calls)

    async def fake_notify_consumption_group_cancelled(*args, **kwargs):
        calls.append("consumption_cancel")

    monkeypatch.setattr(booking_service, "notify_consumption_group_cancelled", fake_notify_consumption_group_cancelled)

    result = asyncio.run(
        booking_service.update_booking(
            booking_id=str(booking.id),
            user_id=booking.user_id,
            has_consumption=False,
        )
    )

    assert result.has_consumption is False
    assert calls == ["consumption_cancel"]


def test_create_booking_rejects_past_start_time(monkeypatch):
    async def fake_room_get(_room_id):
        return SimpleNamespace(name="Kantin", is_active=True)

    async def fake_user_get(_user_id):
        return SimpleNamespace(
            full_name="SYIFA MAULIDA",
            username="syifa.maulida",
            division="IT",
            telegram_id=None,
            telegram_username=None,
            external_user_id="67441c735dc2895b9a48782b",
        )

    async def fake_get_group(_group_id):
        return SimpleNamespace(is_active=True)

    async def fake_validation(*args, **kwargs):
        return True, None

    async def fake_conflict(*args, **kwargs):
        return False, None

    monkeypatch.setattr(booking_service.Room, "get", fake_room_get)
    monkeypatch.setattr(booking_service.User, "get", fake_user_get)
    monkeypatch.setattr(booking_service, "get_telegram_group", fake_get_group)
    monkeypatch.setattr(booking_service, "validate_operating_hours", fake_validation)
    monkeypatch.setattr(booking_service, "validate_booking_duration", fake_validation)
    monkeypatch.setattr(booking_service, "check_booking_conflict", fake_conflict)
    monkeypatch.setattr(booking_service, "datetime", FixedDateTime)

    with_error = None
    try:
        asyncio.run(
            booking_service.create_booking(
                user_id=ObjectId(),
                room_id=str(ObjectId()),
                telegram_group_id=-1001111111111,
                title="Meeting Mendadak",
                start_time=datetime(2026, 7, 8, 9, 0, tzinfo=timezone.utc),
                end_time=datetime(2026, 7, 8, 10, 0, tzinfo=timezone.utc),
            )
        )
    except ValueError as exc:
        with_error = str(exc)

    assert with_error == "Booking baru tidak bisa dibuat untuk jam mulai yang sudah lewat"


def test_create_booking_allows_same_day_future_start(monkeypatch):
    async def fake_room_get(_room_id):
        return SimpleNamespace(name="Kantin", is_active=True)

    async def fake_user_get(_user_id):
        return SimpleNamespace(
            full_name="SYIFA MAULIDA",
            username="syifa.maulida",
            division="IT",
            telegram_id=None,
            telegram_username=None,
            external_user_id="67441c735dc2895b9a48782b",
        )

    async def fake_get_group(_group_id):
        return SimpleNamespace(is_active=True)

    async def fake_validation(*args, **kwargs):
        return True, None

    async def fake_conflict(*args, **kwargs):
        return False, None

    async def fake_find_one(_query):
        return None

    async def fake_history(*args, **kwargs):
        return None

    async def fake_generate_booking_number():
        return "BK-09999"

    monkeypatch.setattr(booking_service.Room, "get", fake_room_get)
    monkeypatch.setattr(booking_service.User, "get", fake_user_get)
    monkeypatch.setattr(booking_service, "get_telegram_group", fake_get_group)
    monkeypatch.setattr(booking_service, "validate_operating_hours", fake_validation)
    monkeypatch.setattr(booking_service, "validate_booking_duration", fake_validation)
    monkeypatch.setattr(booking_service, "check_booking_conflict", fake_conflict)
    monkeypatch.setattr(booking_service.Setting, "find_one", fake_find_one)
    monkeypatch.setattr(booking_service, "create_history", fake_history)
    monkeypatch.setattr(booking_service, "generate_booking_number", fake_generate_booking_number)
    monkeypatch.setattr(booking_service, "Booking", FakeCreatedBooking)
    monkeypatch.setattr(booking_service, "datetime", FixedDateTime)

    result = asyncio.run(
        booking_service.create_booking(
            user_id=ObjectId(),
            room_id=str(ObjectId()),
            telegram_group_id=-1001111111111,
            title="Meeting Mendadak",
            start_time=datetime(2026, 7, 8, 11, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc),
            verification_group_id=-4881064745,
        )
    )

    assert result.booking_number == "BK-09999"
    assert result.published is False


def test_publish_late_draft_still_succeeds(monkeypatch):
    booking = FakeBooking(published=False)
    calls: list[str] = []
    _install_common_mocks(monkeypatch, booking, calls)

    async def fake_notify_new_booking(*args, **kwargs):
        calls.append("main")

    async def fake_notify_verification_group_booking(*args, **kwargs):
        calls.append("verification")

    async def fake_notify_consumption_group(*args, **kwargs):
        calls.append("consumption")

    monkeypatch.setattr(booking_service, "notify_new_booking", fake_notify_new_booking)
    monkeypatch.setattr(booking_service, "notify_verification_group_booking", fake_notify_verification_group_booking)
    monkeypatch.setattr(booking_service, "notify_consumption_group", fake_notify_consumption_group)
    monkeypatch.setattr(booking_service, "datetime", FixedDateTime)

    result = asyncio.run(
        booking_service.publish_booking(
            booking_id=str(booking.id),
            user_id=booking.user_id,
        )
    )

    assert result.published is True
    assert calls == ["main", "verification", "consumption"]
