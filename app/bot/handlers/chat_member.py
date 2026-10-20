import logging
from datetime import datetime, timezone
from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import ChatMemberHandler, ContextTypes
from pymongo.errors import DuplicateKeyError

from app.models.telegram_group import TelegramGroup

logger = logging.getLogger(__name__)


def _is_present(member) -> bool:
    """True when the bot is inside the chat; a restricted bot still counts if it is a member."""
    if member.status in {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR}:
        return True
    return member.status == ChatMemberStatus.RESTRICTED and bool(getattr(member, "is_member", False))


async def handle_bot_membership_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Synchronize Telegram group activity from the bot's membership updates."""
    membership = update.my_chat_member
    if not membership:
        return

    bot_id = context.bot.id
    if membership.new_chat_member.user.id != bot_id:
        return

    old_status = membership.old_chat_member.status
    new_status = membership.new_chat_member.status
    chat = membership.chat
    logger.info(
        "Bot membership update: chat_id=%s type=%s %s -> %s",
        chat.id, chat.type, old_status, new_status,
    )
    if chat.type not in {"group", "supergroup"}:
        return

    group_id = chat.id
    group_name = chat.title or f"Group {group_id}"

    was_present = _is_present(membership.old_chat_member)
    is_present = _is_present(membership.new_chat_member)

    if was_present and not is_present:
        existing = await TelegramGroup.find_one({"group_id": group_id})
        if not existing or not existing.is_active:
            return

        existing.is_active = False
        existing.updated_at = datetime.now(timezone.utc)
        try:
            await existing.save()
        except Exception:
            logger.exception("Failed to deactivate Telegram group %s", group_id)
        else:
            logger.info("Telegram group deactivated after bot removal: group_id=%s", group_id)
        return

    if was_present or not is_present:
        return

    existing = await TelegramGroup.find_one({"group_id": group_id})
    if existing:
        if not existing.is_active:
            existing.is_active = True
            existing.updated_at = datetime.now(timezone.utc)
            try:
                await existing.save()
            except Exception:
                logger.exception("Failed to reactivate Telegram group %s", group_id)
                return
            logger.info("Telegram group reactivated after bot rejoin: group_id=%s", group_id)
        else:
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
