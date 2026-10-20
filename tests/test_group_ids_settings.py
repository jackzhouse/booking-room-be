import asyncio
from types import SimpleNamespace

from app.api.v1 import admin


class _KeyField:
    """`Setting.key == "x"` yields "x", which FakeSetting.find_one uses as the lookup key."""

    def __eq__(self, other):
        return other

    __hash__ = object.__hash__


class FakeSetting:
    """Stands in for the Setting document: one in-memory row per key."""

    rows = {}
    saved = []
    key = _KeyField()

    def __init__(self, key, value, description=None, updated_by=None):
        self.key = key
        self.value = value
        self.updated_by = updated_by

    @classmethod
    async def find_one(cls, query):
        return cls.rows.get(query)

    async def insert(self):
        FakeSetting.rows[self.key] = self

    async def save(self):
        FakeSetting.rows[self.key] = self
        FakeSetting.saved.append(self.key)


def _put(monkeypatch, body, existing=None):
    FakeSetting.saved = []
    FakeSetting.rows = {
        key: FakeSetting(key, value) for key, value in (existing or {}).items()
    }
    monkeypatch.setattr(admin, "Setting", FakeSetting)
    data = admin.GroupIdsUpdate(**body)
    asyncio.run(admin.update_group_ids(data, current_user=SimpleNamespace(id="u-1")))
    return {key: row.value for key, row in FakeSetting.rows.items()}


def test_null_clears_a_default_group(monkeypatch):
    stored = _put(
        monkeypatch,
        {"default_consumption_group_id": None, "default_verification_group_id": -3},
        existing={"default_consumption_group_id": "-2", "default_verification_group_id": "-9"},
    )

    assert stored["default_consumption_group_id"] == ""
    assert stored["default_verification_group_id"] == "-3"
    assert sorted(FakeSetting.saved) == ["default_consumption_group_id", "default_verification_group_id"]


def test_omitted_field_keeps_its_value(monkeypatch):
    stored = _put(
        monkeypatch,
        {"default_verification_group_id": -3},
        existing={"default_consumption_group_id": "-2", "default_verification_group_id": "-9"},
    )

    assert stored["default_consumption_group_id"] == "-2"
    assert stored["default_verification_group_id"] == "-3"


def test_clearing_a_setting_that_does_not_exist_yet_stores_empty(monkeypatch):
    stored = _put(monkeypatch, {"default_consumption_group_id": None})

    assert stored == {"default_consumption_group_id": ""}
