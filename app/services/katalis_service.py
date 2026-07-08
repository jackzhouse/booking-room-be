from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx

from app.core.config import settings


class ExternalAuthError(Exception):
    def __init__(self, message: str, status_code: int = 503, endpoint: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.endpoint = endpoint


def normalize_token(token: Optional[str]) -> str:
    if not token:
        return ""
    return token.strip().removeprefix("Bearer ").removeprefix("bearer ").strip()


def get_authorization_token(authorization: Optional[str], fallback: Optional[str] = None) -> str:
    return normalize_token(authorization or fallback)


def extract_external_user_id(data: Dict[str, Any]) -> Optional[str]:
    return (
        data.get("accountId")
        or data.get("account_id")
        or data.get("external_user_id")
        or data.get("id")
        or data.get("userId")
        or data.get("user_id")
    )


def extract_company_id(data: Dict[str, Any]) -> Optional[str]:
    return data.get("companyId") or data.get("company_id") or data.get("lastCompanyId")


def get_display_name(data: Dict[str, Any]) -> str:
    return data.get("userName") or data.get("accountName") or data.get("name") or data.get("fullName") or "User"


def get_nested_name(data: Dict[str, Any], key: str) -> Optional[str]:
    value = data.get(key)
    if isinstance(value, dict):
        return value.get("name")
    if isinstance(value, str):
        return value
    return None


def get_nested_id(data: Dict[str, Any], key: str) -> Optional[str]:
    value = data.get(key)
    if isinstance(value, dict):
        return value.get("id") or value.get("_id")
    if isinstance(value, str):
        return value
    return None


def extract_items(payload: Any, preferred_key: str) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if not isinstance(payload, dict):
        return []

    for key in (preferred_key, "content", "items", "rows", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = extract_items(value, preferred_key)
            if nested:
                return nested

    return []


def extract_total_pages(payload: Any) -> Optional[int]:
    if not isinstance(payload, dict):
        return None

    for key in ("totalPages", "total_pages", "pages"):
        value = payload.get(key)
        if isinstance(value, int):
            return value

    data = payload.get("data")
    if isinstance(data, dict):
        return extract_total_pages(data)

    return None


class KatalisService:
    def __init__(self) -> None:
        self.base_url = settings.KATALIS_BASE_URL.rstrip("/") + "/"

    def build_url(self, path: str) -> str:
        return urljoin(self.base_url, path.lstrip("/"))

    async def get_json(self, path: str, token: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        endpoint = path
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(
                    self.build_url(path),
                    params=params,
                    headers={"Authorization": f"Bearer {normalize_token(token)}"},
                )
        except httpx.HTTPError as exc:
            raise ExternalAuthError("Layanan external auth sedang bermasalah", endpoint=endpoint) from exc

        if response.status_code >= 400:
            raise ExternalAuthError(
                "Layanan external auth menolak token atau request",
                status_code=response.status_code,
                endpoint=endpoint,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ExternalAuthError("Response external auth tidak valid", endpoint=endpoint) from exc

        if not isinstance(payload, dict):
            raise ExternalAuthError("Response external auth tidak valid", endpoint=endpoint)

        return payload

    async def get_current_employee(self, token: str) -> Dict[str, Any]:
        payload = await self.get_json(settings.KATALIS_CREDENTIAL_CHECK_PATH, token)
        user = payload.get("user")
        if isinstance(user, dict):
            return user

        data = payload.get("data")
        if isinstance(data, dict):
            if isinstance(data.get("user"), dict):
                return data["user"]
            return data

        return payload

    async def fetch_paginated(self, path: str, token: str, preferred_key: str, size: int = 100) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        page = 1

        while page <= 200:
            payload = await self.get_json(path, token, params={"page": page, "size": size})
            page_items = extract_items(payload, preferred_key)
            items.extend(page_items)

            total_pages = extract_total_pages(payload)
            if total_pages is not None:
                if page >= total_pages:
                    break
            elif len(page_items) < size:
                break

            page += 1

        return items

    async def fetch_employees(self, token: str) -> List[Dict[str, Any]]:
        return await self.fetch_paginated(settings.KATALIS_EMPLOYEES_PATH, token, "employees")

    async def fetch_divisions(self, token: str) -> List[Dict[str, Any]]:
        return await self.fetch_paginated(settings.KATALIS_DIVISIONS_PATH, token, "divisions")


katalis_service = KatalisService()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
