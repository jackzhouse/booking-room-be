import logging
from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import ChatMemberHandler, ContextTypes
from pymongo.errors import DuplicateKeyError

from app.models.telegram_group import TelegramGroup

logger = logging.getLogger(__name__)


async def handle_bot_membership_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Register a group when Telegram reports that this bot has joined it."""
    membership = update.my_chat_member
    if not membership:
        return

    bot_id = context.bot.id
    if membership.new_chat_member.user.id != bot_id:
        return

    old_status = membership.old_chat_member.status
    new_status = membership.new_chat_member.status
    if old_status not in {ChatMemberStatus.LEFT, ChatMemberStatus.BANNED}:
        return
    if new_status not in {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR}:
        return

    chat = membership.chat
    if chat.type not in {"group", "supergroup"}:
        return

    group_id = chat.id
    group_name = chat.title or f"Group {group_id}"

    if await TelegramGroup.find_one({"group_id": group_id}):
        logger.info("Telegram group %s already registered; preserving admin state", group_id)
        return

    try:
        await TelegramGroup(
            group_id=group_id,
            group_name=group_name,
            is_active=True,
        ).insert()
    except DuplicateKeyError:
        logger.info("Telegram group %s was registered by a concurrent update", group_id)
        return
    except Exception:
        logger.exception("Failed to register Telegram group %s", group_id)
        return

    logger.info("Telegram group registered successfully: group_id=%s name=%r", group_id, group_name)

    welcome_message = (
        "TKI Room Bot berhasil bergabung.\n\n"
        "Grup ini sudah terdaftar di sistem TKI Room.\n"
        f"Nama grup: {group_name}\n"
        f"ID grup: {group_id}\n\n"
        "Gunakan /schedule untuk melihat jadwal ruangan.\n"
        "Gunakan /schedule DD-MM-YYYY untuk melihat jadwal pada tanggal tertentu."
    )
    try:
        await chat.send_message(welcome_message)
    except Exception:
        logger.exception("Group %s registered but welcome message could not be sent", group_id)
    else:
        logger.info("Telegram group welcome message sent successfully: group_id=%s", group_id)


def get_chat_member_handler():
    """Create handler for Telegram's canonical bot-membership update."""
    return ChatMemberHandler(
        callback=handle_bot_membership_update,
        chat_member_types=ChatMemberHandler.MY_CHAT_MEMBER,
        block=False,
    )
