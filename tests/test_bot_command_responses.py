import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.bot.handlers import cancel, mybooking, schedule, start
from app.bot.handlers.reply import TELEGRAM_MESSAGE_LIMIT, reply_in_chunks


class Query:
    def sort(self, *_args):
        return self

    async def to_list(self):
        return self.items


class Field:
    def __eq__(self, value):
        return ("telegram_id", value)


class FakeUserModel:
    telegram_id = Field()
    result = None

    @classmethod
    async def find_one(cls, _query):
        return cls.result


class FakeRoomModel:
    is_active = Field()
    name = Field()
    query = None

    @classmethod
    def find(cls, _query):
        return cls.query


class FakeBookingModel:
    room_id = Field()
    status = Field()
    start_time = Field()
    user_id = Field()
    booking_number = Field()
    query = None
    result = None

    @classmethod
    def find(cls, _query):
        return cls.query

    @classmethod
    async def find_one(cls, _query):
        return cls.result


def make_update():
    message = SimpleNamespace(reply_text=AsyncMock())
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=101, first_name="R&D [Ops]", username="r_and_d"),
        message=message,
    )


def test_start_with_markdown_characters_uses_plain_text(monkeypatch):
    update = make_update()
    FakeUserModel.result = None
    monkeypatch.setattr(start, "User", FakeUserModel)
    monkeypatch.setattr(start.settings, "FRONTEND_URL", "https://booking.test/app_(new)")

    asyncio.run(start.start(update, SimpleNamespace()))

    text, = update.message.reply_text.call_args.args
    assert "R&D [Ops]" in text
    assert update.message.reply_text.call_args.kwargs.get("parse_mode") is None


def test_start_includes_mini_app_button(monkeypatch):
    update = make_update()
    FakeUserModel.result = None
    monkeypatch.setattr(start, "User", FakeUserModel)
    monkeypatch.setattr(start.settings, "TELEGRAM_MINI_APP_URL", "https://booking.test/telegram")

    asyncio.run(start.start(update, SimpleNamespace()))

    markup = update.message.reply_text.call_args.kwargs["reply_markup"]
    button = markup.inline_keyboard[0][0]
    assert button.web_app.url == "https://booking.test/telegram"


def test_schedule_with_markdown_characters_uses_plain_text(monkeypatch):
    update = make_update()
    db_user = SimpleNamespace(id="user-1")
    room = SimpleNamespace(id="room-1", name="Ruang [R&D]")
    booking = SimpleNamespace(
        title="Plan *urgent* [v2]",
        user_snapshot=SimpleNamespace(full_name="Dewi_Arum", division="R&D"),
        start_time=datetime(2026, 9, 15, 9),
        end_time=datetime(2026, 9, 15, 10),
    )
    rooms = Query()
    rooms.items = [room]
    bookings = Query()
    bookings.items = [booking]
    FakeUserModel.result = db_user
    FakeRoomModel.query = rooms
    FakeBookingModel.query = bookings
    monkeypatch.setattr(schedule, "User", FakeUserModel)
    monkeypatch.setattr(schedule, "Room", FakeRoomModel)
    monkeypatch.setattr(schedule, "Booking", FakeBookingModel)

    asyncio.run(schedule.schedule(update, SimpleNamespace(args=[])))

    text, = update.message.reply_text.call_args.args
    assert "Plan *urgent* [v2]" in text
    assert update.message.reply_text.call_args.kwargs.get("parse_mode") is None


def test_mybooking_with_markdown_characters_uses_plain_text(monkeypatch):
    update = make_update()
    db_user = SimpleNamespace(id="user-1", full_name="Dewi [Ops]", division="R&D")
    booking = SimpleNamespace(
        booking_number="BK-00123",
        room_snapshot=SimpleNamespace(name="Ruang *Utama*"),
        title="Plan [v2]",
        start_time=datetime(2026, 9, 15, 9),
        end_time=datetime(2026, 9, 15, 10),
    )
    bookings = Query()
    bookings.items = [booking]
    FakeUserModel.result = db_user
    FakeBookingModel.query = bookings
    monkeypatch.setattr(mybooking, "User", FakeUserModel)
    monkeypatch.setattr(mybooking, "Booking", FakeBookingModel)

    asyncio.run(mybooking.mybooking(update, SimpleNamespace()))

    text, = update.message.reply_text.call_args.args
    assert "Plan [v2]" in text
    assert update.message.reply_text.call_args.kwargs.get("parse_mode") is None


def test_cancel_with_markdown_characters_uses_plain_text(monkeypatch):
    update = make_update()
    db_user = SimpleNamespace(id="user-1", is_admin=False, role="ROLE_USER")
    booking = SimpleNamespace(
        id="booking-1",
        booking_number="BK-00123",
        user_id="user-1",
        room_snapshot=SimpleNamespace(name="Ruang *Utama*"),
        title="Plan [v2]",
        start_time=datetime(2026, 9, 15, 9),
        end_time=datetime(2026, 9, 15, 10),
        status="active",
    )
    FakeUserModel.result = db_user
    FakeBookingModel.result = booking
    monkeypatch.setattr(cancel, "User", FakeUserModel)
    monkeypatch.setattr(cancel, "Booking", FakeBookingModel)
    monkeypatch.setattr(cancel, "cancel_booking", AsyncMock())

    asyncio.run(cancel.cancel(update, SimpleNamespace(args=["BK-00123"])))

    text, = update.message.reply_text.call_args.args
    assert "Plan [v2]" in text
    assert update.message.reply_text.call_args.kwargs.get("parse_mode") is None


def test_long_response_is_split_under_telegram_limit():
    message = SimpleNamespace(reply_text=AsyncMock())
    text = "A" * (TELEGRAM_MESSAGE_LIMIT + 1)

    asyncio.run(reply_in_chunks(message, text))

    assert message.reply_text.await_count == 2
    assert all(
        len(call.args[0]) <= TELEGRAM_MESSAGE_LIMIT
        for call in message.reply_text.await_args_list
    )
    assert "".join(call.args[0] for call in message.reply_text.await_args_list) == text
