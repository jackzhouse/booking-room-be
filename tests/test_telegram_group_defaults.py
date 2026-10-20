import asyncio
from datetime import datetime
from types import SimpleNamespace

from app.api.v1 import telegram_groups
from app.schemas.telegram_group import TelegramGroupResponse


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


def _group(group_id):
    return TelegramGroupResponse(
        _id=str(group_id),
        group_id=group_id,
        group_name=f"Grup {group_id}",
        is_active=True,
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
    )


def _patch_list(monkeypatch, settings, groups):
    async def fake_find_one(query):
        value = settings.get(query["key"])
        return SimpleNamespace(value=value) if value is not None else None

    async def fake_get_all():
        return groups

    monkeypatch.setattr(telegram_groups.Setting, "find_one", fake_find_one)
    monkeypatch.setattr(telegram_groups, "get_all_telegram_groups", fake_get_all)
    monkeypatch.setattr(telegram_groups, "convert_group_to_response", lambda group: group)


def test_group_list_hides_default_consumption_and_verification_groups(monkeypatch):
    _patch_list(
        monkeypatch,
        {"default_consumption_group_id": "-2", "default_verification_group_id": "-3"},
        [_group(-1), _group(-2), _group(-3)],
    )

    result = asyncio.run(telegram_groups.get_telegram_groups_list(is_filter=True, current_user=object()))

    assert [group.group_id for group in result.groups] == [-1]
    assert result.total == 1


def test_group_list_keeps_everything_when_filter_is_off(monkeypatch):
    _patch_list(
        monkeypatch,
        {"default_consumption_group_id": "-2", "default_verification_group_id": "-3"},
        [_group(-1), _group(-2), _group(-3)],
    )

    result = asyncio.run(telegram_groups.get_telegram_groups_list(is_filter=False, current_user=object()))

    assert [group.group_id for group in result.groups] == [-1, -2, -3]


def test_group_list_ignores_cleared_or_missing_defaults(monkeypatch):
    _patch_list(monkeypatch, {"default_consumption_group_id": ""}, [_group(-1), _group(-2)])

    result = asyncio.run(telegram_groups.get_telegram_groups_list(is_filter=True, current_user=object()))

    assert [group.group_id for group in result.groups] == [-1, -2]
