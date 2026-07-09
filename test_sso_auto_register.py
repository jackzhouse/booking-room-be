from datetime import datetime, timezone

import pytest

from app.api.v1 import auth as auth_module
from app.schemas.auth import SSOLoginRequest
from app.services.katalis_service import katalis_service


class FakeUser:
    external_user_id = "external_user_id"

    find_one_result = None
    saved_instances = []

    def __init__(self, **kwargs):
        self.id = kwargs.pop("id", "user-doc-id")
        self.telegram_id = kwargs.pop("telegram_id", None)
        self.full_name = kwargs.pop("full_name", "User")
        self.username = kwargs.pop("username", None)
        self.avatar_url = kwargs.pop("avatar_url", None)
        self.division = kwargs.pop("division", None)
        self.email = kwargs.pop("email", None)
        self.account_id = kwargs.pop("account_id", None)
        self.company_id = kwargs.pop("company_id", None)
        self.role = kwargs.pop("role", None)
        self.user_type = kwargs.pop("user_type", None)
        self.telegram_username = kwargs.pop("telegram_username", None)
        self.external_user_id = kwargs.pop("external_user_id", None)
        self.external_company_id = kwargs.pop("external_company_id", None)
        self.external_producer = kwargs.pop("external_producer", None)
        self.attendance_user_id = kwargs.pop("attendance_user_id", None)
        self.employee_no = kwargs.pop("employee_no", None)
        self.department_id = kwargs.pop("department_id", None)
        self.department_name = kwargs.pop("department_name", None)
        self.job_title = kwargs.pop("job_title", None)
        self.manager_external_id = kwargs.pop("manager_external_id", None)
        self.last_synced_at = kwargs.pop("last_synced_at", None)
        self.created_by = kwargs.pop("created_by", None)
        self.updated_by = kwargs.pop("updated_by", None)
        self.deleted_by = kwargs.pop("deleted_by", None)
        self.gender = kwargs.pop("gender", None)
        self.nip = kwargs.pop("nip", None)
        self.phone = kwargs.pop("phone", None)
        self.password = kwargs.pop("password", None)
        self.deleted_at = kwargs.pop("deleted_at", None)
        self.is_deleted = kwargs.pop("is_deleted", False)
        self.is_admin = kwargs.pop("is_admin", False)
        self.is_active = kwargs.pop("is_active", True)
        self.created_at = kwargs.pop("created_at", datetime(2026, 7, 8, tzinfo=timezone.utc))
        self.updated_at = kwargs.pop("updated_at", datetime(2026, 7, 8, tzinfo=timezone.utc))
        self.last_login_at = kwargs.pop("last_login_at", None)

    @classmethod
    async def find_one(cls, *_args, **_kwargs):
        return cls.find_one_result

    async def save(self):
        self.__class__.saved_instances.append(self)

    def model_dump(self, by_alias: bool = False):
        payload = {
            "_id" if by_alias else "id": self.id,
            "telegram_id": self.telegram_id,
            "full_name": self.full_name,
            "username": self.username,
            "avatar_url": self.avatar_url,
            "division": self.division,
            "email": self.email,
            "account_id": self.account_id,
            "company_id": self.company_id,
            "role": self.role,
            "user_type": self.user_type,
            "telegram_username": self.telegram_username,
            "external_user_id": self.external_user_id,
            "external_company_id": self.external_company_id,
            "external_producer": self.external_producer,
            "attendance_user_id": self.attendance_user_id,
            "employee_no": self.employee_no,
            "department_id": self.department_id,
            "department_name": self.department_name,
            "job_title": self.job_title,
            "manager_external_id": self.manager_external_id,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "deleted_by": self.deleted_by,
            "gender": self.gender,
            "nip": self.nip,
            "phone": self.phone,
            "deleted_at": self.deleted_at,
            "is_deleted": self.is_deleted,
            "is_admin": self.is_admin,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_login_at": self.last_login_at,
            "last_synced_at": self.last_synced_at,
        }
        return payload


def build_account_detail_payload():
    return {
        "data": {
            "userId": "6740422e74739c67c2a1d711",
            "accountId": "6740422f74739c67c2a1d718",
            "companyId": "0000000074739c67c2a1d6fe",
            "userName": "DEMO QA - ADMIN",
            "accountName": "DEMO QA - ADMIN",
            "identityNumber": "EMP-001",
            "phone": "085730342023",
            "email": "demoqa@gmail.com",
            "gender": "MALE",
            "profilePhotoUrl": "https://cdn.example.com/avatar.png",
            "division": {
                "id": "0000000074739c67c2a1d6ff",
                "name": "DEMO QA",
            },
            "position": {
                "id": "position-1",
                "name": "Admin",
            },
            "roles": ["ROLE_ADMIN", "ROLE_FINANCE"],
        },
    }


class FakeHttpResponse:
    def __init__(self, status_code: int, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.headers = headers or {}

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def reset_fake_user_state(monkeypatch):
    FakeUser.find_one_result = None
    FakeUser.saved_instances = []
    monkeypatch.setattr(auth_module, "User", FakeUser)


@pytest.mark.asyncio
async def test_sso_auto_registers_missing_user(monkeypatch):
    async def fake_get_current_employee(_token: str):
        return build_account_detail_payload()["data"]

    monkeypatch.setattr(auth_module.katalis_service, "get_current_employee", fake_get_current_employee)

    result = await auth_module.sso_login(
        SSOLoginRequest(external_token="token-123"),
        authorization="Bearer token-123",
    )

    assert result.access_token == "token-123"
    assert result.user.external_user_id == "6740422e74739c67c2a1d711"
    assert result.user.full_name == "DEMO QA - ADMIN"
    assert result.user.department_name == "DEMO QA"
    assert result.user.department_id == "0000000074739c67c2a1d6ff"
    assert result.user.attendance_user_id == "6740422e74739c67c2a1d711"
    assert result.user.account_id == "6740422f74739c67c2a1d718"
    assert result.user.company_id == "0000000074739c67c2a1d6fe"
    assert result.user.external_company_id == "0000000074739c67c2a1d6fe"
    assert result.user.job_title == "Admin"
    assert result.user.employee_no == "EMP-001"
    assert result.user.avatar_url == "https://cdn.example.com/avatar.png"
    assert result.user.phone == "085730342023"
    assert result.user.gender == "MALE"
    assert result.user.nip is None
    assert result.user.role == "ROLE_USER"
    assert result.user.user_type == "KATALIS"
    assert result.user.role == "ROLE_USER"
    assert result.user.is_admin is False
    assert len(FakeUser.saved_instances) == 1


@pytest.mark.asyncio
async def test_sso_refreshes_existing_user_without_overwriting_role_or_status(monkeypatch):
    existing_user = FakeUser(
        id="existing-user",
        full_name="Old Name",
        username="olduser",
        email="old@example.com",
        division="Old Division",
        external_user_id="acc-123",
        external_company_id="old-company",
        is_admin=True,
        is_active=False,
    )
    FakeUser.find_one_result = existing_user

    async def fake_get_current_employee(_token: str):
        payload = build_account_detail_payload()
        payload["data"]["userName"] = "john.new"
        payload["data"]["email"] = "john.new@example.com"
        return payload["data"]

    monkeypatch.setattr(auth_module.katalis_service, "get_current_employee", fake_get_current_employee)

    with pytest.raises(auth_module.HTTPException) as exc_info:
        await auth_module.sso_login(
            SSOLoginRequest(external_token="token-123"),
            authorization="Bearer token-123",
        )

    assert exc_info.value.status_code == 403
    assert existing_user.username == "john.new"
    assert existing_user.email == "john.new@example.com"
    assert existing_user.department_name == "DEMO QA"
    assert existing_user.department_id == "0000000074739c67c2a1d6ff"
    assert existing_user.company_id == "0000000074739c67c2a1d6fe"
    assert existing_user.role == "ROLE_SUPER_ADMIN"
    assert existing_user.is_admin is True
    assert existing_user.is_active is False
    assert len(FakeUser.saved_instances) == 0


@pytest.mark.asyncio
async def test_get_current_employee_exchanges_token_before_fetching_detail(monkeypatch):
    detail_payload = build_account_detail_payload()["data"]
    calls = []

    async def fake_request_json(path: str, token: str, params=None, base_url=None):
        calls.append((path, token, params, base_url))
        if path == auth_module.settings.KATALIS_ACCOUNT_DETAIL_PATH and token == "login-token":
            return FakeHttpResponse(401, {})
        if path == auth_module.settings.KATALIS_CREDENTIAL_CHECK_PATH:
            return FakeHttpResponse(200, {}, headers={"Authorization": "Bearer final-token"})
        if path == auth_module.settings.KATALIS_ACCOUNT_DETAIL_PATH and token == "final-token":
            return FakeHttpResponse(200, {"data": detail_payload})
        raise AssertionError(f"Unexpected call: {path} {token}")

    monkeypatch.setattr(katalis_service, "request_json", fake_request_json)

    result = await katalis_service.get_current_employee("login-token")

    assert result["userId"] == "6740422e74739c67c2a1d711"
    assert result["accountId"] == "6740422f74739c67c2a1d718"
    assert calls[0][0] == auth_module.settings.KATALIS_ACCOUNT_DETAIL_PATH
    assert calls[0][3] == katalis_service.account_detail_base_url
    assert calls[1][0] == auth_module.settings.KATALIS_CREDENTIAL_CHECK_PATH
    assert calls[1][3] is None
    assert calls[2][0] == auth_module.settings.KATALIS_ACCOUNT_DETAIL_PATH
    assert calls[2][3] == katalis_service.account_detail_base_url
