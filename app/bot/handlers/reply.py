TELEGRAM_MESSAGE_LIMIT = 4096


async def reply_in_chunks(message, text: str) -> None:
    """Send Telegram text without exceeding Telegram's per-message limit."""
    remaining = text
    while remaining:
        if len(remaining) <= TELEGRAM_MESSAGE_LIMIT:
            await message.reply_text(remaining)
            return

        split_at = remaining.rfind("\n", 0, TELEGRAM_MESSAGE_LIMIT + 1)
        if split_at <= 0:
            split_at = remaining.rfind(" ", 0, TELEGRAM_MESSAGE_LIMIT + 1)
        if split_at <= 0:
            split_at = TELEGRAM_MESSAGE_LIMIT

        await message.reply_text(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
