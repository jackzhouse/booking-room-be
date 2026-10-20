import asyncio
from types import SimpleNamespace

import pytest

from app.services import telegram_service


class FakeGroup(SimpleNamespace):
    saved = 0

    async def save(self):
        FakeGroup.saved += 1


def _patch_existing(monkeypatch, existing):
    class FakeModel:
        group_id = None
        inserted = []

        def __init__(self, **data):
            self.__dict__.update(data)

        @classmethod
        async def find_one(cls, _query):
            return existing

        async def insert(self):
            type(self).inserted.append(self)

    monkeypatch.setattr(telegram_service, "TelegramGroup", FakeModel)
    return FakeModel


def test_adding_a_deactivated_group_reactivates_it(monkeypatch):
    FakeGroup.saved = 0
    existing = FakeGroup(group_id=-100, group_name="Lama", is_active=False, updated_at=None)
    model = _patch_existing(monkeypatch, existing)

    result = asyncio.run(telegram_service.add_telegram_group(-100, "Baru"))

    assert result is existing
    assert existing.is_active is True
    assert existing.group_name == "Baru"
    assert existing.updated_at is not None
    assert FakeGroup.saved == 1
    assert model.inserted == []


def test_adding_an_active_group_is_still_rejected(monkeypatch):
    existing = FakeGroup(group_id=-100, group_name="Lama", is_active=True)
    _patch_existing(monkeypatch, existing)

    with pytest.raises(ValueError):
        asyncio.run(telegram_service.add_telegram_group(-100, "Baru"))


def test_adding_an_unknown_group_inserts_it(monkeypatch):
    model = _patch_existing(monkeypatch, None)

    result = asyncio.run(telegram_service.add_telegram_group(-200, "Baru"))

    assert model.inserted == [result]
    assert result.is_active is True
