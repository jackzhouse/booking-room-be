import pytest

from app.api import deps


class ExternalUserIdField:
    def __eq__(self, other):
        return ("external_user_id", other)


class FakeUser:
    external_user_id = ExternalUserIdField()
    find_one_results = []
    find_one_queries = []
    get_calls = []

    def __init__(self, user_id="user-doc-id", is_active=True):
        self.id = user_id
        self.is_active = is_active

    @classmethod
    async def find_one(cls, query):
        cls.find_one_queries.append(query)
        if cls.find_one_results:
            return cls.find_one_results.pop(0)
        return None

    @classmethod
    async def get(cls, user_id):
        cls.get_calls.append(user_id)
        return cls(user_id=user_id)


class FakeCredentials:
    def __init__(self, token):
        self.credentials = token


@pytest.fixture(autouse=True)
def reset_fake_user(monkeypatch):
    FakeUser.find_one_results = []
    FakeUser.find_one_queries = []
    FakeUser.get_calls = []
    monkeypatch.setattr(deps, "User", FakeUser)


@pytest.mark.asyncio
async def test_katalis_jwt_without_sub_uses_external_claims_before_local_jwt(monkeypatch):
    expected_user = FakeUser(user_id="existing-user")
    FakeUser.find_one_results = [expected_user]

    monkeypatch.setattr(
        deps,
        "verify_external_token",
        lambda _token: {
            "producer": "katalis",
            "userId": "user-123",
            "accountId": "account-123",
            "companyId": "company-123",
        },
    )

    def fail_if_local_decode_runs(_token):
        raise AssertionError("Katalis token must not require local JWT sub")

    monkeypatch.setattr(deps, "decode_access_token", fail_if_local_decode_runs)

    user = await deps.get_current_user(FakeCredentials("katalis-token"))

    assert user is expected_user
    assert FakeUser.find_one_queries == [("external_user_id", "account-123")]
    assert FakeUser.get_calls == []


@pytest.mark.asyncio
async def test_katalis_jwt_falls_back_from_account_id_to_user_id(monkeypatch):
    expected_user = FakeUser(user_id="existing-user")
    FakeUser.find_one_results = [None, expected_user]

    monkeypatch.setattr(
        deps,
        "verify_external_token",
        lambda _token: {
            "producer": "katalis",
            "userId": "user-123",
            "accountId": "account-123",
            "companyId": "company-123",
        },
    )
    monkeypatch.setattr(deps, "decode_access_token", lambda _token: None)

    user = await deps.get_current_user(FakeCredentials("katalis-token"))

    assert user is expected_user
    assert FakeUser.find_one_queries == [
        ("external_user_id", "account-123"),
        ("external_user_id", "user-123"),
    ]


@pytest.mark.asyncio
async def test_local_jwt_still_uses_sub_when_not_katalis(monkeypatch):
    monkeypatch.setattr(deps, "verify_external_token", lambda _token: None)
    monkeypatch.setattr(deps, "decode_access_token", lambda _token: {"sub": "local-user-id"})

    user = await deps.get_current_user(FakeCredentials("booking-token"))

    assert user.id == "local-user-id"
    assert FakeUser.get_calls == ["local-user-id"]
