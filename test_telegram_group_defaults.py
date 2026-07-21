import asyncio
from types import SimpleNamespace

from app.api.v1 import telegram_groups


def test_booking_group_defaults_returns_configured_consumption_group(monkeypatch):
    async def fake_find_one(_query):
        return SimpleNamespace(value="-100123")

    monkeypatch.setattr(telegram_groups.Setting, "find_one", fake_find_one)

    result = asyncio.run(telegram_groups.get_booking_group_defaults(current_user=object()))

    assert result == {"default_consumption_group_id": -100123}


def test_booking_group_defaults_returns_null_for_missing_or_invalid_setting(monkeypatch):
    async def fake_find_one(_query):
        return SimpleNamespace(value="invalid")

    monkeypatch.setattr(telegram_groups.Setting, "find_one", fake_find_one)

    result = asyncio.run(telegram_groups.get_booking_group_defaults(current_user=object()))

    assert result == {"default_consumption_group_id": None}
