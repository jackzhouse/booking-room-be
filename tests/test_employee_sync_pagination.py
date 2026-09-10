import pytest

from app.services.katalis_service import katalis_service


@pytest.mark.asyncio
async def test_employee_sync_fetches_short_pages_without_pagination_metadata(monkeypatch):
    calls = []
    pages = [
        {"data": [{"userId": f"employee-{index}"} for index in range(77)]},
        {"data": [{"userId": f"employee-{index}"} for index in range(77, 154)]},
        {"data": [{"userId": f"employee-{index}"} for index in range(154, 180)]},
        {"data": []},
    ]

    async def fake_get_json(path, token, params=None, base_url=None):
        calls.append((path, token, params, base_url))
        return pages[params["page"] - 1]

    monkeypatch.setattr(katalis_service, "get_json", fake_get_json)

    employees = await katalis_service.fetch_employees("sync-token")

    assert len(employees) == 180
    assert [call[2] for call in calls] == [
        {"page": 1, "size": 100},
        {"page": 2, "size": 100},
        {"page": 3, "size": 100},
        {"page": 4, "size": 100},
    ]


@pytest.mark.asyncio
async def test_employee_sync_stops_when_unpaged_source_repeats_a_page(monkeypatch):
    calls = []
    payload = {"data": [{"userId": "employee-1"}]}

    async def fake_get_json(path, token, params=None, base_url=None):
        calls.append(params)
        return payload

    monkeypatch.setattr(katalis_service, "get_json", fake_get_json)

    employees = await katalis_service.fetch_employees("sync-token")

    assert employees == payload["data"]
    assert calls == [{"page": 1, "size": 100}, {"page": 2, "size": 100}]
