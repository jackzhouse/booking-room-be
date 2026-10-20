import asyncio
from types import SimpleNamespace

import pytest

from app.bot.handlers import topic


class FakeMessage:
    def __init__(self, *, thread_id=None, is_topic_message=False, created=None, edited=None):
        self.message_thread_id = thread_id
        self.is_topic_message = is_topic_message
        self.forum_topic_created = created
        self.forum_topic_edited = edited
        self.replies: list[str] = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


def _update(message, *, chat_type="supergroup"):
    return SimpleNamespace(
        effective_message=message,
        effective_chat=SimpleNamespace(id=-1001, type=chat_type),
        effective_user=SimpleNamespace(id=42),
    )


def _context(status="administrator", args=None):
    async def get_chat_member(chat_id, user_id):
        return SimpleNamespace(status=status)

    return SimpleNamespace(bot=SimpleNamespace(get_chat_member=get_chat_member), args=args or [])


class _StoredCalls(list):
    def __init__(self):
        super().__init__()
        self.registered = {"value": True}


@pytest.fixture
def stored(monkeypatch):
    calls = _StoredCalls()
    registered = calls.registered

    async def fake_set_group_topic(chat_id, message_thread_id, topic_name=None):
        calls.append((chat_id, message_thread_id, topic_name))
        return SimpleNamespace() if registered["value"] else None

    monkeypatch.setattr(topic, "set_group_topic", fake_set_group_topic)
    return calls


@pytest.mark.parametrize("name", ["tkiRoom", "TKIROOM", " tkiroom "])
def test_topic_created_with_matching_name_is_stored(stored, name):
    message = FakeMessage(thread_id=9, created=SimpleNamespace(name=name))

    asyncio.run(topic.handle_topic_event(_update(message), _context()))

    assert stored == [(-1001, 9, "tkiRoom")]
    assert "tkiRoom" in message.replies[0]


def test_topic_renamed_to_tkiroom_is_stored(stored):
    message = FakeMessage(thread_id=9, edited=SimpleNamespace(name="tkiRoom"))

    asyncio.run(topic.handle_topic_event(_update(message), _context()))

    assert stored == [(-1001, 9, "tkiRoom")]


@pytest.mark.parametrize("created,edited", [
    (SimpleNamespace(name="Umum"), None),
    (None, SimpleNamespace(name=None)),
])
def test_other_topics_are_ignored(stored, created, edited):
    message = FakeMessage(thread_id=9, created=created, edited=edited)

    asyncio.run(topic.handle_topic_event(_update(message), _context()))

    assert stored == []
    assert message.replies == []


def test_topic_event_in_unregistered_group_stays_silent(stored):
    stored.registered["value"] = False
    message = FakeMessage(thread_id=9, created=SimpleNamespace(name="tkiRoom"))

    asyncio.run(topic.handle_topic_event(_update(message), _context()))

    assert message.replies == []


def test_settopic_inside_topic_stores_thread(stored):
    message = FakeMessage(thread_id=15, is_topic_message=True)

    asyncio.run(topic.settopic(_update(message), _context()))

    assert stored == [(-1001, 15, "tkiRoom")]
    assert message.replies[0].startswith("✅")


def test_settopic_outside_topic_is_rejected(stored):
    message = FakeMessage(thread_id=None, is_topic_message=False)

    asyncio.run(topic.settopic(_update(message), _context()))

    assert stored == []
    assert message.replies[0].startswith("❌")


def test_settopic_requires_group_admin(stored):
    message = FakeMessage(thread_id=15, is_topic_message=True)

    asyncio.run(topic.settopic(_update(message), _context(status="member")))

    assert stored == []
    assert "admin grup" in message.replies[0]


def test_settopic_rejects_private_chat(stored):
    message = FakeMessage(thread_id=15, is_topic_message=True)

    asyncio.run(topic.settopic(_update(message, chat_type="private"), _context()))

    assert stored == []


def test_settopic_hapus_clears_topic(stored):
    message = FakeMessage()

    asyncio.run(topic.settopic(_update(message), _context(args=["hapus"])))

    assert stored == [(-1001, None, None)]
    assert "dihapus" in message.replies[0]
