from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx

from app.core.config import settings

DEFAULT_ACCOUNT_DETAIL_FALLBACK_PATH = "/api/v1/admin/employees/account/detail"


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
    user = data.get("user")
    if isinstance(user, dict):
        return user.get("userId") or user.get("external_user_id") or user.get("id")

    return (
        data.get("userId")
        or data.get("external_user_id")
        or data.get("user_id")
        or data.get("accountId")
        or data.get("account_id")
        or data.get("id")
    )


def extract_account_id(data: Dict[str, Any]) -> Optional[str]:
    user = data.get("user")
    if isinstance(user, dict):
        accounts = user.get("accounts")
        if isinstance(accounts, list):
            for account in accounts:
                if isinstance(account, dict):
                    account_id = account.get("id") or account.get("_id")
                    if account_id:
                        return str(account_id)

    return data.get("accountId") or data.get("account_id")


def extract_company_id(data: Dict[str, Any]) -> Optional[str]:
    active_company = data.get("activeCompany")
    if isinstance(active_company, dict):
        company_id = active_company.get("id") or active_company.get("_id")
        if company_id:
            return str(company_id)

    return data.get("companyId") or data.get("company_id") or data.get("lastCompanyId")


def extract_role(data: Dict[str, Any]) -> Optional[str]:
    roles = data.get("roles")
    if isinstance(roles, list) and roles:
        return str(roles[0])
    role = data.get("role")
    if role:
        return str(role)
    return None


def extract_user_type(data: Dict[str, Any]) -> Optional[str]:
    return data.get("user_type") or data.get("userType")


def extract_user_profile(data: Dict[str, Any]) -> Dict[str, Any]:
    user = data.get("user")
    if isinstance(user, dict):
        return user
    return data


def extract_company_profile(data: Dict[str, Any]) -> Dict[str, Any]:
    active_company = data.get("activeCompany")
    if isinstance(active_company, dict):
        return active_company

    companies = data.get("companies")
    if isinstance(companies, list):
        for company in companies:
            if isinstance(company, dict):
                return company

    return {}


def set_user_attr(user: Any, field: str, value: Any) -> None:
    if hasattr(user, field):
        setattr(user, field, value)


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


def clean_email(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = value.strip()
    if "@" not in value:
        return None
    return value


def parse_active_flag(value: Any, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in {"false", "0", "inactive", "nonaktif"}
    if value is None:
        return fallback
    return bool(value)


def populate_user_from_employee(user: Any, employee: Dict[str, Any], *, allow_active_update: bool = False) -> Any:
    profile = extract_user_profile(employee)
    company = extract_company_profile(employee)

    division_name = get_nested_name(profile, "division") or profile.get("divisionName") or company.get("name")
    division_id = get_nested_id(profile, "division") or profile.get("divisionId") or extract_company_id(employee)
    position_name = get_nested_name(profile, "position") or profile.get("positionName")
    manager = profile.get("manager")
    manager_external_id = None
    if isinstance(manager, dict):
        manager_external_id = extract_external_user_id(manager)

    user.full_name = profile.get("userName") or profile.get("accountName") or profile.get("name") or profile.get("fullName") or get_display_name(profile)
    user.username = profile.get("username") or profile.get("userName") or user.username
    user.email = clean_email(profile.get("email"))
    user.avatar_url = profile.get("profilePhotoUrl") or profile.get("photoUrl") or profile.get("avatar_url") or user.avatar_url
    user.external_user_id = extract_external_user_id(employee) or user.external_user_id
    set_user_attr(user, "account_id", extract_account_id(employee) or getattr(user, "account_id", None))
    company_id = extract_company_id(employee)
    user.external_company_id = company_id or user.external_company_id
    set_user_attr(user, "company_id", company_id or getattr(user, "company_id", None))
    user.external_producer = profile.get("producer") or employee.get("producer") or employee.get("lastService") or settings.KATALIS_PRODUCER
    set_user_attr(user, "role", getattr(user, "role", None) or ("ROLE_SUPER_ADMIN" if getattr(user, "is_admin", False) else "ROLE_USER"))
    set_user_attr(user, "user_type", getattr(user, "user_type", None) or (str(user.external_producer).upper() if user.external_producer else None))
    user.attendance_user_id = profile.get("userId") or profile.get("attendanceUserId") or profile.get("id") or user.attendance_user_id
    user.employee_no = profile.get("identityNumber") or profile.get("employeeNo") or profile.get("employee_no") or profile.get("nik") or profile.get("nip")
    user.department_id = division_id
    user.department_name = division_name
    user.division = division_name
    user.job_title = position_name
    user.manager_external_id = manager_external_id
    user.gender = profile.get("gender") or profile.get("sex") or user.gender
    user.phone = profile.get("phone") or profile.get("phoneNumber") or user.phone
    user.nip = profile.get("npwp") or profile.get("nip") or user.nip
    user.last_synced_at = now_utc()
    user.updated_at = now_utc()

    if allow_active_update:
        user.is_active = parse_active_flag(employee.get("active"), user.is_active)

    return user


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
        self.account_detail_base_url = settings.KATALIS_ACCOUNT_DETAIL_BASE_URL.rstrip("/") + "/"
        self.directory_base_url = settings.KATALIS_DIRECTORY_BASE_URL.rstrip("/") + "/"

    def build_url(self, path: str, *, base_url: Optional[str] = None) -> str:
        return urljoin((base_url or self.base_url), path.lstrip("/"))

    def get_account_detail_paths(self) -> List[str]:
        paths = [settings.KATALIS_ACCOUNT_DETAIL_PATH]
        if settings.KATALIS_ACCOUNT_DETAIL_PATH != DEFAULT_ACCOUNT_DETAIL_FALLBACK_PATH:
            paths.append(DEFAULT_ACCOUNT_DETAIL_FALLBACK_PATH)
        return paths

    async def request_json(
        self,
        path: str,
        token: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        base_url: Optional[str] = None,
    ) -> httpx.Response:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                return await client.get(
                    self.build_url(path, base_url=base_url),
                    params=params,
                    headers={"Authorization": f"Bearer {normalize_token(token)}"},
                )
        except httpx.HTTPError as exc:
            raise ExternalAuthError("Layanan external auth sedang bermasalah", endpoint=path) from exc

    async def get_json(
        self,
        path: str,
        token: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        endpoint = path
        response = await self.request_json(path, token, params=params, base_url=base_url)

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

    async def exchange_credential_token(self, token: str) -> str:
        endpoint = settings.KATALIS_CREDENTIAL_CHECK_PATH
        response = await self.request_json(endpoint, token)

        if response.status_code >= 400:
            raise ExternalAuthError(
                "Layanan external auth menolak token atau request",
                status_code=response.status_code,
                endpoint=endpoint,
            )

        headers = response.headers
        header_token = (
            headers.get("authorization")
            or headers.get("Authorization")
            or headers.get("x-token")
            or headers.get("X-Token")
        )

        body_token = None
        try:
            payload = response.json()
        except ValueError:
            payload = {}

        if isinstance(payload, dict):
            data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
            body_token = (
                data.get("token")
                or data.get("access_token")
                or payload.get("token")
                or payload.get("access_token")
            )

        final_token = normalize_token(header_token or body_token)
        if not final_token:
            raise ExternalAuthError("Token credential tidak ditemukan dari layanan Katalis", endpoint=endpoint)

        return final_token

    async def get_current_employee(self, token: str) -> Dict[str, Any]:
        last_error: Optional[ExternalAuthError] = None

        for path in self.get_account_detail_paths():
            try:
                payload = await self.get_json(path, token, base_url=self.account_detail_base_url)
                data = payload.get("data")
                if isinstance(data, dict):
                    return data
                return payload
            except ExternalAuthError as exc:
                last_error = exc
                if exc.status_code == 404:
                    continue
                if exc.status_code in {401, 403}:
                    final_token = await self.exchange_credential_token(token)
                    retry_payload = await self.get_json(path, final_token, base_url=self.account_detail_base_url)
                    data = retry_payload.get("data")
                    if isinstance(data, dict):
                        return data
                    return retry_payload
                raise

        if last_error is not None:
            raise last_error
        raise ExternalAuthError("Layanan external auth sedang bermasalah")

    async def fetch_paginated(
        self,
        path: str,
        token: str,
        preferred_key: str,
        size: int = 100,
        *,
        base_url: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        page = 1

        while page <= 200:
            payload = await self.get_json(path, token, params={"page": page, "size": size}, base_url=base_url)
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
        return await self.fetch_paginated(
            settings.KATALIS_EMPLOYEES_PATH,
            token,
            "employees",
            base_url=self.directory_base_url,
        )

    async def fetch_divisions(self, token: str) -> List[Dict[str, Any]]:
        return await self.fetch_paginated(
            settings.KATALIS_DIVISIONS_PATH,
            token,
            "divisions",
            base_url=self.directory_base_url,
        )


katalis_service = KatalisService()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
