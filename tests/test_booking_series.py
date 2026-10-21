import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, create_autospec

import pytest
from bson import ObjectId
from pydantic import ValidationError

from app.models.booking import TelegramMessageRef
from app.schemas.booking import BookingSeriesCreate
from app.services import booking_service, telegram_service
from tests.test_booking_notifications import FakeBooking, FixedDateTime, _install_common_mocks

SERIES_ID = "series-1"


def _member(day: int, **kwargs) -> FakeBooking:
    booking = FakeBooking(**kwargs)
    booking.series_id = SERIES_ID
    booking.start_time = datetime(2026, 7, day, 7, 0, tzinfo=timezone.utc)
    booking.end_time = datetime(2026, 7, day, 9, 0, tzinfo=timezone.utc)
    return booking


def _slot(day: int, hour: int = 2) -> tuple[datetime, datetime]:
    start = datetime(2026, 7, day, hour, 0, tzinfo=timezone.utc)
    return start, start + timedelta(hours=2)


def _install_series(monkeypatch, members: list[FakeBooking]):
    async def fake_get_series(_series_id):
        return members

    monkeypatch.setattr(booking_service, "get_booking_series", fake_get_series)


def _install_create_mocks(monkeypatch, conflict_days: set[int] | None = None):
    async def fake_room_get(_room_id):
        return SimpleNamespace(name="Kantin", is_active=True)

    async def fake_valid(*args, **kwargs):
        return True, None

    async def fake_conflict(_room_id, start, end):
        if start.day in (conflict_days or set()):
            return True, SimpleNamespace(id=ObjectId())
        return False, None

    async def fake_conflict_message(_booking):
        return "Ruangan sudah dipakai"

    monkeypatch.setattr(booking_service.Room, "get", fake_room_get)
    monkeypatch.setattr(booking_service, "validate_operating_hours", fake_valid)
    monkeypatch.setattr(booking_service, "validate_booking_duration", fake_valid)
    monkeypatch.setattr(booking_service, "check_booking_conflict", fake_conflict)
    monkeypatch.setattr(booking_service, "format_conflict_message", fake_conflict_message)
    monkeypatch.setattr(booking_service, "datetime", FixedDateTime)


def _create_series(slots):
    return booking_service.create_booking_series(
        user_id=ObjectId(),
        room_id=str(ObjectId()),
        telegram_group_id=-1001111111111,
        title="Onboarding Sales",
        slots=slots,
    )


def test_series_schema_requires_at_least_one_day():
    base = {"room_id": "r", "telegram_group_id": -1, "title": "t"}
    with pytest.raises(ValidationError):
        BookingSeriesCreate(**base, slots=[])

    slot = {"start_time": "2026-07-09T09:00:00+07:00", "end_time": "2026-07-09T11:00:00+07:00"}
    assert len(BookingSeriesCreate(**base, slots=[slot]).slots) == 1


def test_generate_booking_number_increments_in_one_atomic_update(monkeypatch):
    collection = SimpleNamespace(find_one_and_update=AsyncMock(return_value={"value": "42"}))
    monkeypatch.setattr(booking_service.Setting, "get_motor_collection", lambda: collection)

    assert asyncio.run(booking_service.generate_booking_number()) == "BK-00042"

    flt, pipeline = collection.find_one_and_update.await_args.args
    assert flt == {"key": "booking_counter"}
    assert isinstance(pipeline, list)  # aggregation-pipeline update, so the read and +1 are one operation
    assert collection.find_one_and_update.await_args.kwargs["upsert"] is True


def test_series_with_blocked_day_saves_nothing_and_lists_every_blocked_day(monkeypatch):
    _install_create_mocks(monkeypatch, conflict_days={9, 11})
    fake_create = create_autospec(booking_service.create_booking, spec_set=True)
    monkeypatch.setattr(booking_service, "create_booking", fake_create)

    with pytest.raises(booking_service.SeriesConflictError) as exc:
        asyncio.run(_create_series([_slot(9), _slot(10), _slot(11)]))

    assert [c["date"] for c in exc.value.conflicts] == ["2026-07-09", "2026-07-11"]
    assert exc.value.conflicts[0]["reason"] == "Ruangan sudah dipakai"
    fake_create.assert_not_called()


@pytest.mark.parametrize(
    "slots, message",
    [
        ([], "Pilih 1 sampai 14 hari"),
        ([_slot(9, 1 + i % 20) for i in range(15)], "Pilih 1 sampai 14 hari"),
        ([_slot(9, 1), _slot(9, 5)], "Tanggal booking tidak boleh dobel"),
        ([(_slot(9)[1], _slot(9)[0])], "Jam selesai harus setelah jam mulai pada hari yang sama"),
    ],
)
def test_series_rejects_malformed_days(monkeypatch, slots, message):
    _install_create_mocks(monkeypatch)

    with pytest.raises(ValueError, match=message):
        asyncio.run(_create_series(slots))


def test_series_creates_days_in_date_order_with_one_series_id(monkeypatch):
    _install_create_mocks(monkeypatch)
    created: list[dict] = []

    async def fake_create(**kwargs):
        created.append(kwargs)
        return SimpleNamespace(**kwargs)

    monkeypatch.setattr(booking_service, "create_booking", fake_create)

    series_id, bookings = asyncio.run(_create_series([_slot(11), _slot(9), _slot(10, 5)]))

    assert [b.start_time.day for b in bookings] == [9, 10, 11]
    assert {b.series_id for b in bookings} == {series_id}
    assert bookings[1].start_time.hour == 5  # a day keeps its own hours


def test_series_removes_created_days_when_a_later_day_fails(monkeypatch):
    _install_create_mocks(monkeypatch)
    calls = {"n": 0}

    async def flaky_create(**kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise ValueError("Grup Telegram tidak ditemukan atau tidak aktif")
        return SimpleNamespace(**kwargs)

    discard = create_autospec(booking_service._discard_bookings, spec_set=True)
    monkeypatch.setattr(booking_service, "create_booking", flaky_create)
    monkeypatch.setattr(booking_service, "_discard_bookings", discard)

    with pytest.raises(ValueError, match="Grup Telegram"):
        asyncio.run(_create_series([_slot(9), _slot(10)]))

    (undone,) = discard.await_args.args
    assert [b.start_time.day for b in undone] == [9]


def test_publish_series_sends_one_message_per_target_and_shares_refs(monkeypatch):
    members = [_member(9, published=False), _member(10, published=False)]
    owner = members[0].user_id
    for member in members:
        member.user_id = owner
    _install_series(monkeypatch, members)
    _install_common_mocks(monkeypatch, members[0], [])

    sent: list[str] = []

    async def fake_notify_series(bookings, role, kind, **kwargs):
        sent.append(f"{role}:{kind}:{len(bookings)}")
        return TelegramMessageRef(chat_id=1, message_id=len(sent))

    monkeypatch.setattr(booking_service, "notify_series", fake_notify_series)
    monkeypatch.setattr(booking_service, "datetime", FixedDateTime)

    result = asyncio.run(booking_service.publish_booking_series(SERIES_ID, owner))

    assert sent == ["main:new:2", "verification:new:2", "consumption:new:2"]
    assert all(m.published for m in result)
    for member in members:  # edit later targets the same message from any day
        assert member.telegram_messages["main"].message_id == 1


def test_publish_single_day_of_a_series_publishes_the_whole_series(monkeypatch):
    members = [_member(9, published=False), _member(10, published=False)]
    _install_common_mocks(monkeypatch, members[1], [])
    publish_series = create_autospec(booking_service.publish_booking_series, spec_set=True)
    publish_series.return_value = members
    monkeypatch.setattr(booking_service, "publish_booking_series", publish_series)

    result = asyncio.run(
        booking_service.publish_booking(str(members[1].id), members[1].user_id)
    )

    assert result is members[1]
    publish_series.assert_awaited_once_with(SERIES_ID, members[1].user_id, False)


def test_series_day_cannot_change_shared_details_or_move_date(monkeypatch):
    booking = _member(9)
    _install_common_mocks(monkeypatch, booking, [])
    _install_series(monkeypatch, [booking, _member(10)])

    for kwargs, expected in (
        ({"title": "Judul Lain"}, "Tidak bisa mengubah: judul"),
        ({"consumption_group_id": -999}, "Tidak bisa mengubah: grup konsumsi"),
        (
            {
                "start_time": booking.start_time + timedelta(days=1),
                "end_time": booking.end_time + timedelta(days=1),
            },
            "Tanggal booking dalam seri tidak bisa diubah",
        ),
    ):
        with pytest.raises(ValueError, match=expected):
            asyncio.run(
                booking_service.update_booking(
                    booking_id=str(booking.id), user_id=booking.user_id, **kwargs
                )
            )


def test_series_day_hours_edit_the_combined_message_instead_of_sending_new_ones(monkeypatch):
    booking = _member(9, published=True)
    _install_common_mocks(monkeypatch, booking, [])
    _install_series(monkeypatch, [booking, _member(10, published=True)])

    async def fake_valid(*args, **kwargs):
        return True, None

    async def fake_no_conflict(*args, **kwargs):
        return False, None

    refresh = create_autospec(booking_service._refresh_series_messages, spec_set=True)
    per_day_update = create_autospec(booking_service.notify_booking_updated, spec_set=True)
    monkeypatch.setattr(booking_service, "validate_operating_hours", fake_valid)
    monkeypatch.setattr(booking_service, "validate_booking_duration", fake_valid)
    monkeypatch.setattr(booking_service, "check_booking_conflict", fake_no_conflict)
    monkeypatch.setattr(booking_service, "_refresh_series_messages", refresh)
    monkeypatch.setattr(booking_service, "notify_booking_updated", per_day_update)

    asyncio.run(
        booking_service.update_booking(
            booking_id=str(booking.id),
            user_id=booking.user_id,
            title=booking.title,
            start_time=booking.start_time + timedelta(hours=1),
            end_time=booking.end_time + timedelta(hours=1),
        )
    )

    refresh.assert_awaited_once()
    assert refresh.await_args.args == (SERIES_ID,)
    assert refresh.await_args.kwargs["changed_ids"] == frozenset({booking.id})
    per_day_update.assert_not_called()


def test_cancel_series_skips_ended_and_cancelled_days(monkeypatch):
    ended = _member(7)
    already_cancelled = _member(9, status="cancelled")
    upcoming = [_member(10), _member(11)]
    members = [ended, already_cancelled, *upcoming]
    owner = ended.user_id
    for member in members:
        member.user_id = owner
    _install_series(monkeypatch, members)
    _install_common_mocks(monkeypatch, upcoming[0], [])
    monkeypatch.setattr(booking_service, "datetime", FixedDateTime)  # "now" = 2026-07-08 10:00 UTC

    notified: list[tuple[str, str, int]] = []

    async def fake_notify_series(bookings, role, kind, **kwargs):
        notified.append((role, kind, len(bookings)))

    refresh = create_autospec(booking_service._refresh_series_messages, spec_set=True)
    monkeypatch.setattr(booking_service, "notify_series", fake_notify_series)
    monkeypatch.setattr(booking_service, "_refresh_series_messages", refresh)

    asyncio.run(booking_service.cancel_booking_series(SERIES_ID, owner))

    assert [m.status for m in members] == ["active", "cancelled", "cancelled", "cancelled"]
    assert notified == [("main", "cancelled", 2), ("verification", "cancelled", 2), ("consumption", "cancelled", 2)]
    refresh.assert_awaited_once_with(SERIES_ID)


def test_cancel_series_requires_owner_or_admin(monkeypatch):
    members = [_member(10)]
    _install_series(monkeypatch, members)

    with pytest.raises(ValueError, match="tidak memiliki akses"):
        asyncio.run(booking_service.cancel_booking_series(SERIES_ID, ObjectId()))
    assert members[0].status == "active"


def test_series_message_lists_every_day_and_marks_changes():
    changed, cancelled, plain = _member(9), _member(10, status="cancelled"), _member(11)

    text = telegram_service._render_series_notification(
        [changed, cancelled, plain],
        "main",
        "updated",
        changed_ids=frozenset({changed.id}),
        changed_fields=["jadwal Kamis, 9 Jul 2026"],
    )

    assert "Perubahan Penggunaan Ruang Meeting" in text
    assert "Kamis, 9 Juli 2026, 14.00 sampai 16.00 WIB (diubah)" in text
    assert "<s>Jumat, 10 Juli 2026, 14.00 sampai 16.00 WIB</s> (dibatalkan)" in text
    assert "• Sabtu, 11 Juli 2026, 14.00 sampai 16.00 WIB" in text
    assert text.count("<b>Jadwal:</b>") == 1


def test_series_consumption_message_carries_facilities_and_note():
    text = telegram_service._render_series_notification([_member(9), _member(10)], "consumption", "new")

    assert "Permintaan Konsumsi Ruang Meeting" in text
    assert "• AC" in text and "• test" in text


def test_series_update_edits_earlier_message_and_new_or_cancelled_send_fresh_ones(monkeypatch):
    sent: list[str] = []
    edited: list[str] = []

    async def fake_send(chat_id, message, parse_mode="HTML"):
        sent.append(message)
        return TelegramMessageRef(chat_id=chat_id, message_id=50)

    async def fake_edit(ref, message, parse_mode="HTML"):
        edited.append(message)
        return True

    monkeypatch.setattr(telegram_service, "send_telegram_message", fake_send)
    monkeypatch.setattr(telegram_service, "edit_telegram_message", fake_edit)
    members = [_member(9), _member(10)]
    ref = TelegramMessageRef(chat_id=members[0].telegram_group_id, message_id=7)

    asyncio.run(telegram_service.notify_series(members, "main", "updated", message_ref=ref))
    asyncio.run(telegram_service.notify_series(members, "main", "new"))
    asyncio.run(telegram_service.notify_series(members, "main", "cancelled"))

    assert len(edited) == 1 and len(sent) == 2


def test_draft_series_day_edits_details_and_copies_them_to_other_draft_days(monkeypatch):
    days = [_member(9, published=False), _member(10, published=False), _member(11, published=True)]
    booking = days[0]
    _install_common_mocks(monkeypatch, booking, [])
    _install_series(monkeypatch, days)
    for member in days[1:]:
        member.save = AsyncMock()

    asyncio.run(
        booking_service.update_booking(
            booking_id=str(booking.id), user_id=booking.user_id, title="judul baru", description="Deskripsi baru"
        )
    )

    assert booking.title == "Judul Baru"
    assert days[1].title == "Judul Baru"
    assert days[1].description == booking.description
    days[1].save.assert_awaited_once()
    assert days[2].title != "Judul Baru"
    days[2].save.assert_not_called()


def test_series_that_lost_its_other_days_edits_like_a_plain_booking(monkeypatch):
    booking = _member(9, published=True)
    _install_common_mocks(monkeypatch, booking, [])
    _install_series(monkeypatch, [booking])

    async def fake_valid(*args, **kwargs):
        return True, None

    monkeypatch.setattr(booking_service, "validate_operating_hours", fake_valid)
    monkeypatch.setattr(booking_service, "validate_booking_duration", fake_valid)
    monkeypatch.setattr(
        booking_service, "_refresh_series_messages", create_autospec(booking_service._refresh_series_messages, spec_set=True)
    )

    asyncio.run(booking_service.update_booking(booking_id=str(booking.id), user_id=booking.user_id, title="judul baru"))

    assert booking.title == "Judul Baru"
