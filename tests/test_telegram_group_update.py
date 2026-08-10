import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1 import telegram_groups
from app.schemas.telegram_group import TelegramGroupUpdate


def test_update_telegram_group_returns_updated_response(monkeypatch):
    group = SimpleNamespace(
        id="507f1f77bcf86cd799439011",
        group_id=-100123,
        group_name="Updated group",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        model_dump=lambda by_alias: {
            "_id": "507f1f77bcf86cd799439011",
            "group_id": -100123,
            "group_name": "Updated group",
            "is_active": True,
            "created_at": group.created_at,
            "updated_at": group.updated_at,
        },
    )

    async def fake_update(group_id, **data):
        assert group_id == -100123
        assert data == {"group_name": "Updated group"}
        return group

    monkeypatch.setattr(telegram_groups, "update_telegram_group", fake_update)

    result = asyncio.run(
        telegram_groups.update_telegram_group_endpoint(
            -100123,
            TelegramGroupUpdate(group_name="Updated group"),
            current_user=object(),
        )
    )

    assert result.group_id == -100123
    assert result.group_name == "Updated group"


def test_update_telegram_group_returns_404_when_missing(monkeypatch):
    async def fake_update(_group_id, **_data):
        return None

    monkeypatch.setattr(telegram_groups, "update_telegram_group", fake_update)

    with pytest.raises(HTTPException, match="not found") as error:
        asyncio.run(
            telegram_groups.update_telegram_group_endpoint(
                -100123,
                TelegramGroupUpdate(group_name="Updated group"),
                current_user=object(),
            )
        )

    assert error.value.status_code == 404
