import asyncio
from types import SimpleNamespace

import pytest
from telegram.error import BadRequest, NetworkError

from app.models.booking import TelegramMessageRef
from app.services import telegram_service

CHAT_ID = -1003952786718


@pytest.fixture(autouse=True)
def _reset_topic_cache():
    telegram_service.clear_topic_cache()
    yield
    telegram_service.clear_topic_cache()


class FakeBot:
    def __init__(self):
        self.sent: list[dict] = []
        self.edited: list[dict] = []
        self.send_error: Exception | None = None
        self.send_errors_by_thread: dict[int, Exception] = {}
        self.edit_error: Exception | None = None

    async def send_message(self, **kwargs):
        thread_id = kwargs.get("message_thread_id")
        if thread_id in self.send_errors_by_thread:
            raise self.send_errors_by_thread[thread_id]
        if self.send_error:
            raise self.send_error
        self.sent.append(kwargs)
        return SimpleNamespace(message_id=100 + len(self.sent))

    async def edit_message_text(self, **kwargs):
        if self.edit_error:
            raise self.edit_error
        self.edited.append(kwargs)


def _install(monkeypatch, thread_id=None):
    fake_bot = FakeBot()
    cleared: list[tuple] = []

    async def fake_thread_lookup(_chat_id):
        return thread_id

    async def fake_set_group_topic(chat_id, message_thread_id, topic_name=None):
        cleared.append((chat_id, message_thread_id))

    monkeypatch.setattr(telegram_service, "bot", fake_bot)
    monkeypatch.setattr(telegram_service, "get_topic_thread_id", fake_thread_lookup)
    monkeypatch.setattr(telegram_service, "set_group_topic", fake_set_group_topic)
    return fake_bot, cleared


def test_send_returns_ref_and_posts_in_topic(monkeypatch):
    fake_bot, _ = _install(monkeypatch, thread_id=77)

    ref = asyncio.run(telegram_service.send_telegram_message(CHAT_ID, "halo"))

    assert ref == TelegramMessageRef(chat_id=CHAT_ID, message_id=101, message_thread_id=77)
    assert fake_bot.sent[0]["message_thread_id"] == 77


def test_send_without_topic_posts_in_main_chat(monkeypatch):
    fake_bot, _ = _install(monkeypatch, thread_id=None)

    ref = asyncio.run(telegram_service.send_telegram_message(CHAT_ID, "halo"))

    assert ref.message_thread_id is None
    assert fake_bot.sent[0]["message_thread_id"] is None


def test_send_clears_deleted_topic_and_retries_in_main_chat(monkeypatch):
    fake_bot, cleared = _install(monkeypatch, thread_id=77)
    fake_bot.send_errors_by_thread[77] = BadRequest("Message thread not found")

    ref = asyncio.run(telegram_service.send_telegram_message(CHAT_ID, "halo"))

    assert ref == TelegramMessageRef(chat_id=CHAT_ID, message_id=101, message_thread_id=None)
    assert cleared == [(CHAT_ID, None)]
    assert "message_thread_id" not in fake_bot.sent[0]


def test_send_returns_false_on_other_telegram_errors(monkeypatch):
    fake_bot, cleared = _install(monkeypatch, thread_id=77)
    fake_bot.send_error = BadRequest("Chat not found")

    assert asyncio.run(telegram_service.send_telegram_message(CHAT_ID, "halo")) is False
    assert cleared == []


def test_send_or_edit_edits_the_stored_message(monkeypatch):
    fake_bot, _ = _install(monkeypatch)
    ref = TelegramMessageRef(chat_id=CHAT_ID, message_id=5)

    result = asyncio.run(telegram_service.send_or_edit_telegram_message(CHAT_ID, "baru", ref))

    assert result is ref
    assert fake_bot.edited == [
        {"chat_id": CHAT_ID, "message_id": 5, "text": "baru", "parse_mode": "HTML"}
    ]
    assert fake_bot.sent == []


def test_send_or_edit_treats_unchanged_text_as_success(monkeypatch):
    fake_bot, _ = _install(monkeypatch)
    fake_bot.edit_error = BadRequest("Message is not modified")
    ref = TelegramMessageRef(chat_id=CHAT_ID, message_id=5)

    result = asyncio.run(telegram_service.send_or_edit_telegram_message(CHAT_ID, "sama", ref))

    assert result is ref
    assert fake_bot.sent == []


@pytest.mark.parametrize("error", [BadRequest("Message to edit not found"), NetworkError("down")])
def test_send_or_edit_sends_new_message_when_edit_fails(monkeypatch, error):
    fake_bot, _ = _install(monkeypatch)
    fake_bot.edit_error = error
    ref = TelegramMessageRef(chat_id=CHAT_ID, message_id=5)

    result = asyncio.run(telegram_service.send_or_edit_telegram_message(CHAT_ID, "baru", ref))

    assert result == TelegramMessageRef(chat_id=CHAT_ID, message_id=101)
    assert len(fake_bot.sent) == 1


def test_send_or_edit_sends_when_there_is_no_ref_or_the_chat_changed(monkeypatch):
    fake_bot, _ = _install(monkeypatch)
    other_chat_ref = TelegramMessageRef(chat_id=-999, message_id=5)

    asyncio.run(telegram_service.send_or_edit_telegram_message(CHAT_ID, "satu", None))
    asyncio.run(telegram_service.send_or_edit_telegram_message(CHAT_ID, "dua", other_chat_ref))

    assert fake_bot.edited == []
    assert [call["text"] for call in fake_bot.sent] == ["satu", "dua"]
