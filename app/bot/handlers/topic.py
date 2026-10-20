"""
Handlers that find the forum topic ("tkiRoom") a group's notifications are posted to.

Telegram has no lookup by topic name, so the thread id is captured from the
topic's own service message, or from /settopic run inside the topic.
"""
import logging

from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import ContextTypes

from app.services.telegram_service import set_group_topic

logger = logging.getLogger(__name__)

TOPIC_NAME = "tkiRoom"


def is_notification_topic(name: str | None) -> bool:
    return bool(name) and name.strip().lower() == TOPIC_NAME.lower()


async def handle_topic_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remember the tkiRoom topic when it is created or renamed to that name."""
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None or message.message_thread_id is None:
        return

    topic = message.forum_topic_created or message.forum_topic_edited
    if topic is None or not is_notification_topic(topic.name):
        return

    group = await set_group_topic(chat.id, message.message_thread_id, TOPIC_NAME)
    if group is None:
        logger.info("Topic %s seen in unregistered chat %s, ignoring", TOPIC_NAME, chat.id)
        return

    logger.info("Notifications for %s now go to topic %s", chat.id, message.message_thread_id)
    await message.reply_text(f"✅ Notifikasi booking akan dikirim ke topic {TOPIC_NAME}.")


async def settopic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /settopic       - use the topic this command is sent in
    /settopic hapus - go back to posting in the main chat
    Only group admins may use it.
    """
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if message is None or chat is None or user is None:
        return

    if chat.type not in ("group", "supergroup"):
        await message.reply_text("❌ Perintah ini hanya dapat dipakai di dalam grup.")
        return

    member = await context.bot.get_chat_member(chat.id, user.id)
    if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
        await message.reply_text("❌ Hanya admin grup yang dapat mengatur topic notifikasi.")
        return

    if context.args and context.args[0].lower() == "hapus":
        group = await set_group_topic(chat.id, None)
        reply = (
            "✅ Topic notifikasi dihapus. Notifikasi dikirim ke chat utama grup."
            if group
            else "❌ Grup ini belum terdaftar di Booking Room."
        )
        await message.reply_text(reply)
        return

    if not message.is_topic_message or message.message_thread_id is None:
        await message.reply_text(
            f"❌ Jalankan /settopic di dalam topic {TOPIC_NAME}, bukan di chat utama grup."
        )
        return

    group = await set_group_topic(chat.id, message.message_thread_id, TOPIC_NAME)
    if group is None:
        await message.reply_text("❌ Grup ini belum terdaftar di Booking Room.")
        return

    await message.reply_text(f"✅ Notifikasi booking akan dikirim ke topic ini ({TOPIC_NAME}).")
