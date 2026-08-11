import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from bson import ObjectId

from app.services import booking_service
from app.services import scheduler_service
from app.services import telegram_service


class FakeBooking:
    def __init__(
        self,
        *,
        published: bool = True,
        status: str = "active",
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
        self.status = status
        self.published = published
        self.cancelled_at = None
        self.cancelled_by = None
        self.completed_at = None
        self.has_consumption = has_consumption
        self.consumption_note = "test"
        self.consumption_facilities = ["AC", "Proyektor"]
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

    async def fake_room_get(_room_id):
        return SimpleNamespace(name="Kantin", is_active=True, facilities=["AC", "Proyektor", "TV"])

    async def fake_find_one(_query):
        return SimpleNamespace(value="-5181257488")

    async def fake_create_history(*args, **kwargs):
        return None

    monkeypatch.setattr(booking_service.Booking, "get", fake_booking_get)
    monkeypatch.setattr(booking_service.User, "get", fake_user_get)
    monkeypatch.setattr(booking_service.Room, "get", fake_room_get)
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
            consumption_facilities=[],
        )
    )

    assert result.has_consumption is False
    assert calls == ["consumption_cancel"]


def test_update_booking_saves_selected_consumption_facilities(monkeypatch):
    booking = FakeBooking(published=True, has_consumption=False, consumption_group_id=None)
    booking.consumption_facilities = []
    calls: list[str] = []
    notification_updates: list[bool] = []
    _install_common_mocks(monkeypatch, booking, calls)

    async def fake_notify_consumption_group(*args, **kwargs):
        calls.append("consumption")
        notification_updates.append(kwargs.get("is_update", False))

    monkeypatch.setattr(booking_service, "notify_consumption_group", fake_notify_consumption_group)

    result = asyncio.run(
        booking_service.update_booking(
            booking_id=str(booking.id),
            user_id=booking.user_id,
            consumption_facilities=["AC", "Proyektor"],
        )
    )

    assert result.has_consumption is True
    assert result.consumption_facilities == ["AC", "Proyektor"]
    assert result.consumption_group_id == -5181257488
    assert calls == ["consumption"]
    assert notification_updates == [True]


def test_update_booking_rejects_unavailable_consumption_facility(monkeypatch):
    booking = FakeBooking(published=False)
    calls: list[str] = []
    _install_common_mocks(monkeypatch, booking, calls)

    with_error = None
    try:
        asyncio.run(
            booking_service.update_booking(
                booking_id=str(booking.id),
                user_id=booking.user_id,
                consumption_facilities=["Karaoke"],
            )
        )
    except ValueError as exc:
        with_error = str(exc)

    assert with_error == "Fasilitas tidak tersedia di ruangan: Karaoke"


def test_consumption_notification_includes_selected_facilities(monkeypatch):
    booking = FakeBooking(published=True)
    booking.description = "Koordinasi target\nmingguan"
    booking.consumption_note = "15 nasi box\n15 air mineral"
    sent_messages: list[str] = []

    async def fake_send_telegram_message(_chat_id, message, parse_mode="HTML"):
        sent_messages.append(message)
        return True

    monkeypatch.setattr(telegram_service, "send_telegram_message", fake_send_telegram_message)

    asyncio.run(telegram_service.notify_consumption_group(booking))

    assert "<b>TKI ROOM - PERMINTAAN KONSUMSI</b>" in sent_messages[0]
    assert "<b>Deskripsi:</b>\nKoordinasi target\nmingguan" in sent_messages[0]
    assert "<b>Fasilitas:</b>\n• AC\n• Proyektor" in sent_messages[0]
    assert "<b>Konsumsi:</b>\n• 15 nasi box\n• 15 air mineral" in sent_messages[0]


def test_consumption_update_notification_uses_change_title_and_same_group(monkeypatch):
    booking = FakeBooking(published=True)
    sent_messages: list[tuple[int, str]] = []

    async def fake_send_telegram_message(chat_id, message, parse_mode="HTML"):
        sent_messages.append((chat_id, message))
        return True

    monkeypatch.setattr(telegram_service, "send_telegram_message", fake_send_telegram_message)

    asyncio.run(telegram_service.notify_consumption_group(booking, is_update=True))

    chat_id, message = sent_messages[0]
    assert chat_id == booking.consumption_group_id
    assert "<b>TKI ROOM - PERUBAHAN KONSUMSI</b>" in message
    assert "<b>Deskripsi:</b>\nTests" in message
    assert "<b>Fasilitas:</b>\n• AC\n• Proyektor" in message
    assert "<b>Konsumsi:</b>\n• test" in message


def test_consumption_note_normalizes_existing_bullets_and_blank_lines():
    booking = FakeBooking(published=True)
    booking.consumption_note = "• Minuman\n\n- Gorengan\nMakan siang"

    assert telegram_service._format_consumption_note(booking) == "• Minuman\n• Gorengan\n• Makan siang"


def test_notification_template_escapes_dynamic_values():
    message = telegram_service._render_notification(
        "TKI ROOM - BOOKING BARU",
        [("📍", "Ruang", "Ruang <Utama> & A")],
        "Hubungi PIC <sebelum> lanjut.",
        "BK-<00061>",
        [("📄", "Deskripsi", "Rapat <internal> & final")],
    )

    assert message == (
        "<b>TKI ROOM - BOOKING BARU</b>\n"
        "<code>#BK-&lt;00061&gt;</code>\n\n"
        "<b>Ruang:</b> Ruang &lt;Utama&gt; &amp; A\n\n"
        "<b>Deskripsi:</b>\nRapat &lt;internal&gt; &amp; final\n\n"
        "<b>Tindakan:</b>\nHubungi PIC &lt;sebelum&gt; lanjut."
    )


def test_all_notification_types_use_html_template(monkeypatch):
    booking = FakeBooking(published=True)
    sent_messages: list[tuple[int, str, str]] = []

    async def fake_send_telegram_message(chat_id, message, parse_mode="HTML"):
        sent_messages.append((chat_id, message, parse_mode))
        return True

    async def fake_get_telegram_group(_group_id):
        return SimpleNamespace(group_name="Grup Test")

    monkeypatch.setattr(telegram_service, "send_telegram_message", fake_send_telegram_message)
    monkeypatch.setattr(telegram_service, "get_telegram_group", fake_get_telegram_group)

    async def send_all():
        await telegram_service.notify_new_booking(booking)
        await telegram_service.notify_booking_updated(booking, {}, changed_fields=["judul"])
        await telegram_service.notify_booking_target_removed(booking, -1000000000001, "grup utama")
        await telegram_service.notify_booking_cancelled(booking)
        await telegram_service.test_notification(booking.telegram_group_id)
        await telegram_service.notify_consumption_group(booking)
        await telegram_service.notify_consumption_group(booking, is_update=True)
        await telegram_service.notify_consumption_group_cancelled(booking)
        await telegram_service.notify_verification_group_booking(booking)
        await telegram_service.notify_verification_group_cancelled(booking)
        await telegram_service.notify_verification_group_cleanup(booking)

    asyncio.run(send_all())

    expected_titles = [
        "TKI ROOM - BOOKING BARU",
        "TKI ROOM - PERUBAHAN BOOKING",
        "TKI ROOM - PERUBAHAN TUJUAN NOTIFIKASI",
        "TKI ROOM - PEMBATALAN BOOKING",
        "TKI ROOM - TEST NOTIFIKASI",
        "TKI ROOM - PERMINTAAN KONSUMSI",
        "TKI ROOM - PERUBAHAN KONSUMSI",
        "TKI ROOM - PEMBATALAN KONSUMSI",
        "TKI ROOM - BOOKING BARU",
        "TKI ROOM - PEMBATALAN BOOKING",
        "TKI ROOM - MEETING SELESAI",
    ]
    assert [parse_mode for _, _, parse_mode in sent_messages] == ["HTML"] * len(expected_titles)
    assert [
        f"<b>{title}</b>" in message
        for title, (_, message, _) in zip(expected_titles, sent_messages)
    ] == [True] * len(expected_titles)
    assert all("<b>Tindakan:</b>" in message for _, message, _ in sent_messages)
    assert all(
        not any(icon in message for icon in ["📍", "📅", "⏰", "👤", "🏢", "📝", "📄", "🏷️", "🍴", "ℹ️"])
        for _, message, _ in sent_messages
    )


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


def test_completed_booking_blocks_update_cancel_and_publish(monkeypatch):
    booking = FakeBooking(published=True, status="completed")
    calls: list[str] = []
    _install_common_mocks(monkeypatch, booking, calls)

    for action in (
        lambda: booking_service.update_booking(
            booking_id=str(booking.id),
            user_id=booking.user_id,
            title="Updated Title",
        ),
        lambda: booking_service.cancel_booking(
            booking_id=str(booking.id),
            user_id=booking.user_id,
        ),
        lambda: booking_service.publish_booking(
            booking_id=str(booking.id),
            user_id=booking.user_id,
        ),
    ):
        try:
            asyncio.run(action())
            raise AssertionError("expected ValueError")
        except ValueError as exc:
            assert str(exc) == "Booking sudah selesai"


def test_scheduler_marks_ended_booking_completed(monkeypatch):
    now = datetime(2026, 7, 8, 10, 0, tzinfo=timezone.utc)
    booking = FakeBooking(published=True)
    booking.end_time = datetime(2026, 7, 8, 7, 19, tzinfo=timezone.utc)
    booking.hrd_notified = False
    notify_calls: list[str] = []

    class FakeQuery:
        def __init__(self, result):
            self.result = result

        def sort(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        async def to_list(self):
            return self.result

        async def count(self):
            return len(self.result)

    def fake_find(query):
        if query.get("status") == "active":
            return FakeQuery([booking])
        return FakeQuery([])

    async def fake_notify_verification_group_cleanup(target):
        notify_calls.append(target.booking_number)

    monkeypatch.setattr(scheduler_service.Booking, "find", fake_find)
    monkeypatch.setattr(scheduler_service, "datetime", FixedDateTime)
    monkeypatch.setattr(scheduler_service, "notify_verification_group_cleanup", fake_notify_verification_group_cleanup)

    asyncio.run(scheduler_service.check_and_notify_ended_bookings())

    assert booking.status == "completed"
    assert booking.completed_at is not None
    assert booking.hrd_notified is True
    assert notify_calls == ["BK-00061"]
