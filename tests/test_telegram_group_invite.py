import asyncio
from types import SimpleNamespace

from pymongo.errors import DuplicateKeyError
from telegram.constants import ChatMemberStatus
from telegram.ext import ChatMemberHandler

from app.bot.handlers import chat_member


BOT_ID = 712345678
GROUP_ID = -1001234567890


def make_update(
    *,
    chat_type="supergroup",
    old_status=ChatMemberStatus.LEFT,
    new_status=ChatMemberStatus.MEMBER,
    member_id=BOT_ID,
):
    messages = []

    async def send_message(text):
        messages.append(text)

    chat = SimpleNamespace(
        id=GROUP_ID,
        title="Ruang Rapat",
        type=chat_type,
        send_message=send_message,
    )
    membership = SimpleNamespace(
        chat=chat,
        old_chat_member=SimpleNamespace(status=old_status),
        new_chat_member=SimpleNamespace(
            status=new_status,
            user=SimpleNamespace(id=member_id),
        ),
    )
    return SimpleNamespace(my_chat_member=membership), messages


def context():
    return SimpleNamespace(bot=SimpleNamespace(id=BOT_ID))


def group_model(existing=None, insert_error=None):
    class FakeTelegramGroup:
        inserted = []

        def __init__(self, **data):
            self.__dict__.update(data)

        @classmethod
        async def find_one(cls, _query):
            return existing

        async def insert(self):
            if insert_error:
                raise insert_error
            type(self).inserted.append(self)

    return FakeTelegramGroup


def test_invite_registers_new_group_and_sends_welcome(monkeypatch):
    fake_group = group_model()
    monkeypatch.setattr(chat_member, "TelegramGroup", fake_group)
    update, messages = make_update()

    asyncio.run(chat_member.handle_bot_membership_update(update, context()))

    assert len(fake_group.inserted) == 1
    assert fake_group.inserted[0].group_id == GROUP_ID
    assert fake_group.inserted[0].group_name == "Ruang Rapat"
    assert fake_group.inserted[0].is_active is True
    assert len(messages) == 1
    assert "TKI Room Bot berhasil bergabung" in messages[0]
    assert "/schedule" in messages[0]


def test_existing_group_preserves_admin_state_and_skips_welcome(monkeypatch):
    fake_group = group_model(
        existing=SimpleNamespace(group_id=GROUP_ID, group_name="Admin name", is_active=False)
    )
    monkeypatch.setattr(chat_member, "TelegramGroup", fake_group)
    update, messages = make_update()

    asyncio.run(chat_member.handle_bot_membership_update(update, context()))

    assert fake_group.inserted == []
    assert messages == []


def test_non_invite_or_unsupported_chat_does_not_register_group(monkeypatch):
    fake_group = group_model()
    monkeypatch.setattr(chat_member, "TelegramGroup", fake_group)

    status_update, _ = make_update(old_status=ChatMemberStatus.MEMBER)
    private_update, _ = make_update(chat_type="private")
    other_member_update, _ = make_update(member_id=999)

    asyncio.run(chat_member.handle_bot_membership_update(status_update, context()))
    asyncio.run(chat_member.handle_bot_membership_update(private_update, context()))
    asyncio.run(chat_member.handle_bot_membership_update(other_member_update, context()))

    assert fake_group.inserted == []


def test_concurrent_duplicate_registration_skips_welcome(monkeypatch):
    fake_group = group_model(insert_error=DuplicateKeyError("duplicate group_id"))
    monkeypatch.setattr(chat_member, "TelegramGroup", fake_group)
    update, messages = make_update()

    asyncio.run(chat_member.handle_bot_membership_update(update, context()))

    assert fake_group.inserted == []
    assert messages == []


def test_handler_uses_my_chat_member_updates():
    handler = chat_member.get_chat_member_handler()

    assert isinstance(handler, ChatMemberHandler)
    assert handler.chat_member_types == ChatMemberHandler.MY_CHAT_MEMBER
