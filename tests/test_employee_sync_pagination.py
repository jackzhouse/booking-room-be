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
        return pages[params["page"]]

    monkeypatch.setattr(katalis_service, "get_json", fake_get_json)

    employees = await katalis_service.fetch_employees("sync-token")

    assert len(employees) == 180
    assert [call[2] for call in calls] == [
        {"page": 0, "size": 100},
        {"page": 1, "size": 100},
        {"page": 2, "size": 100},
        {"page": 3, "size": 100},
    ]


@pytest.mark.asyncio
async def test_employee_sync_fetches_zero_based_pages_from_total_pages(monkeypatch):
    calls = []
    pages = {
        0: {
            "totalElements": 177,
            "totalPages": 2,
            "last": False,
            "numberOfElements": 100,
            "data": [{"userId": f"employee-{index}"} for index in range(100)],
        },
        1: {
            "totalElements": 177,
            "totalPages": 2,
            "last": True,
            "numberOfElements": 77,
            "data": [{"userId": f"employee-{index}"} for index in range(100, 177)],
        },
    }

    async def fake_get_json(path, token, params=None, base_url=None):
        calls.append(params)
        return pages[params["page"]]

    monkeypatch.setattr(katalis_service, "get_json", fake_get_json)

    employees = await katalis_service.fetch_employees("sync-token")

    assert len(employees) == 177
    assert calls == [{"page": 0, "size": 100}, {"page": 1, "size": 100}]


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
    assert calls == [{"page": 0, "size": 100}, {"page": 1, "size": 100}]
