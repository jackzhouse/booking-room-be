from datetime import datetime, timedelta, timezone
from hashlib import sha256
import hmac
import json
from urllib.parse import urlencode
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.v1 import auth
from app.core import security
from app.schemas.auth import CurrentUserProfileUpdate, TelegramMiniAppRequest
from app.services import auth_code_service as service_module
from app.bot.handlers import authorize as authorize_handler


class Field:
    def __init__(self, name):
        self.name = name

    def __eq__(self, value):
        return self.name, value


class FakeUser:
    telegram_id = Field("telegram_id")
    users_by_id = {}
    telegram_lookup = {}

    def __init__(
        self,
        user_id,
        *,
        telegram_id=None,
        telegram_username=None,
        full_name="Katalis User",
        external_user_id="external-user",
        account_id="account-id",
        is_active=True,
        is_deleted=False,
    ):
        self.id = user_id
        self.telegram_id = telegram_id
        self.telegram_username = telegram_username
        self.full_name = full_name
        self.external_user_id = external_user_id
        self.account_id = account_id
        self.is_active = is_active
        self.is_deleted = is_deleted
        self.username = "katalis.username"
        self.avatar_url = "https://example.test/avatar.png"
        self.is_admin = False
        self.role = "ROLE_USER"
        self.user_type = "KATALIS"
        self.last_login_at = None
        self.updated_at = None
        self.updated_by = None
        self.saved = False

    @classmethod
    async def get(cls, user_id):
        return cls.users_by_id.get(user_id)

    @classmethod
    async def find_one(cls, query):
        field, value = query
        assert field == "telegram_id"
        return cls.telegram_lookup.get(value)

    async def save(self):
        self.saved = True

    def model_dump(self, **_kwargs):
        now = datetime.now(timezone.utc)
        return {
            "_id": self.id,
            "telegram_id": self.telegram_id,
            "full_name": self.full_name,
            "username": self.username,
            "avatar_url": self.avatar_url,
            "account_id": self.account_id,
            "role": self.role,
            "user_type": self.user_type,
            "telegram_username": self.telegram_username,
            "external_user_id": self.external_user_id,
            "is_admin": self.is_admin,
            "is_active": self.is_active,
            "is_deleted": self.is_deleted,
            "created_at": now,
            "updated_at": self.updated_at or now,
        }


class FakeAuthCode:
    code = Field("code")
    current = None
    pending = []

    @classmethod
    async def find_one(cls, query):
        assert query[0] == "code"
        return cls.current if cls.current and cls.current.code == query[1] else None

    @classmethod
    def find(cls, _query):
        return SimpleNamespace(to_list=AsyncMock(return_value=list(cls.pending)))


class LinkCode:
    def __init__(self, target_user_id, *, expires_at=None, created_at=None):
        self.code = "123456"
        self.purpose = "telegram_link"
        self.target_user_id = target_user_id
        self.telegram_user_id = None
        self.telegram_user_data = None
        self.completion_error = None
        self.used = False
        self.used_at = None
        self.expires_at = expires_at or datetime.now(timezone.utc) + timedelta(minutes=3)
        self.created_at = created_at or datetime.now(timezone.utc)
        self.saved = False

    async def save(self):
        self.saved = True


@pytest.fixture(autouse=True)
def reset_fakes(monkeypatch):
    FakeUser.users_by_id = {}
    FakeUser.telegram_lookup = {}
    FakeAuthCode.current = None
    FakeAuthCode.pending = []
    monkeypatch.setattr(service_module, "User", FakeUser)
    monkeypatch.setattr(service_module, "AuthCode", FakeAuthCode)


def build_init_data(bot_token, auth_date):
    params = {
        "auth_date": str(auth_date),
        "query_id": "test-query",
        "user": json.dumps({"id": 998877, "first_name": "Telegram", "username": "linked"}),
    }
    data_check_string = "\n".join(f"{key}={params[key]}" for key in sorted(params))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), sha256).digest()
    params["hash"] = hmac.new(secret_key, data_check_string.encode(), sha256).hexdigest()
    return urlencode(params)


def test_validate_telegram_init_data_accepts_fresh_signed_payload(monkeypatch):
    bot_token = "123456:test-token"
    monkeypatch.setattr(security.settings, "BOT_TOKEN", bot_token)
    init_data = build_init_data(bot_token, int(datetime.now(timezone.utc).timestamp()))

    user_data, error = security.validate_telegram_init_data(init_data, max_age_seconds=300)

    assert error is None
    assert user_data["id"] == 998877


def test_validate_telegram_init_data_rejects_expired_signed_payload(monkeypatch):
    bot_token = "123456:test-token"
    monkeypatch.setattr(security.settings, "BOT_TOKEN", bot_token)
    old_timestamp = int((datetime.now(timezone.utc) - timedelta(minutes=6)).timestamp())
    init_data = build_init_data(bot_token, old_timestamp)

    user_data, error = security.validate_telegram_init_data(init_data, max_age_seconds=300)

    assert user_data is None
    assert error == "INIT_DATA_EXPIRED"


@pytest.mark.asyncio
async def test_new_link_code_replaces_old_pending_code(monkeypatch):
    old_code = LinkCode(
        "target-user",
        created_at=datetime.now(timezone.utc) - timedelta(seconds=20),
    )
    FakeAuthCode.pending = [old_code]
    generate_code = AsyncMock(return_value=("654321", datetime.now(timezone.utc)))
    monkeypatch.setattr(service_module.auth_code_service, "generate_code", generate_code)

    code, _ = await service_module.auth_code_service.generate_link_code("target-user")

    assert code == "654321"
    assert old_code.used is True
    assert old_code.completion_error == "CODE_REPLACED"
    generate_code.assert_awaited_once_with(
        purpose="telegram_link",
        target_user_id="target-user",
    )


@pytest.mark.asyncio
async def test_link_code_creation_is_rate_limited():
    FakeAuthCode.pending = [LinkCode("target-user")]

    with pytest.raises(service_module.LinkCodeRateLimitError) as exc_info:
        await service_module.auth_code_service.generate_link_code("target-user")

    assert 1 <= exc_info.value.retry_after <= 10


@pytest.mark.asyncio
async def test_link_code_endpoint_returns_stable_rate_limit_error(monkeypatch):
    monkeypatch.setattr(
        auth.auth_code_service,
        "generate_link_code",
        AsyncMock(side_effect=service_module.LinkCodeRateLimitError(7)),
    )

    with pytest.raises(HTTPException) as exc_info:
        await auth.generate_telegram_link_code(FakeUser("target-user"))

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == {
        "code": "LINK_CODE_RATE_LIMITED",
        "message": "Please wait before creating another Telegram link code",
        "retry_after": 7,
    }


@pytest.mark.asyncio
async def test_replaced_link_code_reports_expired_instead_of_conflict():
    replaced = LinkCode("target-user")
    replaced.used = True
    replaced.completion_error = "CODE_REPLACED"
    FakeAuthCode.current = replaced

    status = await service_module.auth_code_service.get_link_status("123456", "target-user")

    assert status["status"] == "expired"
    assert status["error_code"] == "CODE_REPLACED"


@pytest.mark.asyncio
async def test_link_completion_binds_identity_without_overwriting_katalis_profile():
    target = FakeUser("target-user")
    FakeUser.users_by_id[target.id] = target
    FakeAuthCode.current = LinkCode(target.id)

    success, error, linked_user = await service_module.auth_code_service.complete_telegram_link(
        "123456",
        {"id": 998877, "username": "new_name", "first_name": "Telegram"},
    )

    assert success is True
    assert error == ""
    assert linked_user is target
    assert target.telegram_id == 998877
    assert target.telegram_username == "@new_name"
    assert target.full_name == "Katalis User"
    assert target.username == "katalis.username"
    assert FakeAuthCode.current.used is True


@pytest.mark.asyncio
async def test_bot_authorize_completes_link_without_creating_user(monkeypatch):
    message = SimpleNamespace(reply_text=AsyncMock())
    update = SimpleNamespace(
        effective_user=SimpleNamespace(
            id=998877,
            first_name="Telegram",
            last_name="User",
            username="linked",
        ),
        message=message,
    )
    context = SimpleNamespace(args=["123456"], user_data={})
    target = SimpleNamespace(full_name="Katalis User")
    service = SimpleNamespace(
        verify_code=AsyncMock(return_value=SimpleNamespace(purpose="telegram_link")),
        complete_telegram_link=AsyncMock(return_value=(True, "", target)),
        mark_code_used=AsyncMock(),
    )
    create_user = AsyncMock()
    monkeypatch.setattr(authorize_handler, "auth_code_service", service)
    monkeypatch.setattr(authorize_handler, "create_or_update_user", create_user)

    await authorize_handler.authorize_command(update, context)

    service.complete_telegram_link.assert_awaited_once()
    service.mark_code_used.assert_not_awaited()
    create_user.assert_not_awaited()
    assert "berhasil dihubungkan" in message.reply_text.await_args.args[0]


def test_bot_authorize_attempt_limit():
    user_data = {}

    assert all(
        authorize_handler._consume_authorize_attempt(user_data, now=float(second))
        for second in range(5)
    )
    assert authorize_handler._consume_authorize_attempt(user_data, now=5.0) is False
    assert authorize_handler._consume_authorize_attempt(user_data, now=61.0) is True


@pytest.mark.asyncio
async def test_link_completion_blocks_telegram_identity_owned_by_another_user():
    target = FakeUser("target-user")
    existing = FakeUser("existing-user", telegram_id=998877)
    FakeUser.users_by_id[target.id] = target
    FakeUser.telegram_lookup[998877] = existing
    FakeAuthCode.current = LinkCode(target.id)

    success, error, linked_user = await service_module.auth_code_service.complete_telegram_link(
        "123456",
        {"id": 998877, "username": "owner"},
    )

    assert success is False
    assert error == "TELEGRAM_ALREADY_LINKED"
    assert linked_user is None
    assert target.telegram_id is None
    assert FakeAuthCode.current.completion_error == "TELEGRAM_ALREADY_LINKED"


@pytest.mark.asyncio
async def test_existing_login_redeemer_cannot_consume_link_code():
    FakeAuthCode.current = LinkCode("target-user")

    success, error = await service_module.auth_code_service.mark_code_used(
        "123456",
        {"id": 998877},
    )

    assert success is False
    assert error == "LINK_CODE_REQUIRES_LINK_COMPLETION"
    assert FakeAuthCode.current.used is False


@pytest.mark.asyncio
async def test_tma_login_uses_linked_user_and_preserves_external_profile(monkeypatch):
    linked = FakeUser("target-user", telegram_id=998877)
    FakeUser.telegram_lookup[998877] = linked
    monkeypatch.setattr(auth, "User", FakeUser)
    monkeypatch.setattr(
        auth,
        "validate_telegram_init_data",
        lambda *_args, **_kwargs: (
            {"id": 998877, "username": "updated_name", "photo_url": "new-photo"},
            None,
        ),
    )
    monkeypatch.setattr(auth, "create_access_token", lambda data: f"token:{data['sub']}")

    response = await auth.telegram_mini_app_login(TelegramMiniAppRequest(init_data="signed"))

    assert response.access_token == "token:target-user"
    assert response.user.id == "target-user"
    assert linked.telegram_username == "@updated_name"
    assert linked.full_name == "Katalis User"
    assert linked.avatar_url == "https://example.test/avatar.png"


@pytest.mark.asyncio
async def test_tma_login_rejects_unlinked_identity_without_creating_user(monkeypatch):
    monkeypatch.setattr(auth, "User", FakeUser)
    monkeypatch.setattr(
        auth,
        "validate_telegram_init_data",
        lambda *_args, **_kwargs: ({"id": 998877, "username": "unknown"}, None),
    )

    with pytest.raises(HTTPException) as exc_info:
        await auth.telegram_mini_app_login(TelegramMiniAppRequest(init_data="signed"))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "TELEGRAM_NOT_LINKED"


@pytest.mark.asyncio
async def test_linked_user_cannot_manually_replace_verified_username():
    linked = FakeUser(
        "target-user",
        telegram_id=998877,
        telegram_username="@verified_name",
    )

    with pytest.raises(HTTPException) as exc_info:
        await auth.update_current_user_profile(
            CurrentUserProfileUpdate(telegram_username="@different_name"),
            current_user=linked,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "TELEGRAM_USERNAME_MANAGED"
    assert linked.saved is False


@pytest.mark.asyncio
async def test_user_can_disconnect_telegram_without_changing_external_identity():
    linked = FakeUser(
        "target-user",
        telegram_id=998877,
        telegram_username="@verified_name",
    )

    response = await auth.unlink_current_user_telegram(current_user=linked)

    assert linked.telegram_id is None
    assert linked.telegram_username is None
    assert linked.external_user_id == "external-user"
    assert linked.full_name == "Katalis User"
    assert linked.saved is True
    assert response.telegram_id is None
