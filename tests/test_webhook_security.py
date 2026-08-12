import asyncio
import logging
from types import SimpleNamespace

from app.bot.webhook import is_valid_webhook_secret
from app.models.booking import UserSnapshot
from app.core.config import settings
from app import main
from app.main import app


def test_webhook_url_no_longer_embeds_bot_token(monkeypatch):
    monkeypatch.setattr(settings, "WEBHOOK_BASE_URL", "https://example.com/booking/")
    monkeypatch.setattr(settings, "BOT_TOKEN", "bot-token-value")

    assert settings.webhook_url == "https://example.com/booking/api/v1/webhook/telegram"
    assert "bot-token-value" not in settings.webhook_url


def test_new_and_legacy_telegram_webhook_routes_are_registered():
    routes = {(route.path, method) for route in app.routes for method in route.methods or set()}

    assert ("/api/v1/webhook/telegram", "POST") in routes
    assert ("/webhook/telegram", "POST") in routes


def test_webhook_secret_validation(monkeypatch):
    monkeypatch.setattr(settings, "WEBHOOK_SECRET_TOKEN", "super-secret-token")

    assert is_valid_webhook_secret("super-secret-token") is True
    assert is_valid_webhook_secret("wrong-token") is False
    assert is_valid_webhook_secret(None) is False


def test_webhook_secret_optional_for_non_production(monkeypatch):
    monkeypatch.setattr(settings, "WEBHOOK_SECRET_TOKEN", None)

    assert is_valid_webhook_secret(None) is True
    assert is_valid_webhook_secret("anything") is True


def test_webhook_logs_dispatch_success(monkeypatch, caplog):
    async def fake_handle_webhook_update(data, _context):
        assert data == {"update_id": 123, "my_chat_member": {}}

    async def request_json():
        return {"update_id": 123, "my_chat_member": {}}

    monkeypatch.setattr(main, "handle_webhook_update", fake_handle_webhook_update)
    monkeypatch.setattr(settings, "WEBHOOK_SECRET_TOKEN", "expected-secret")
    caplog.set_level(logging.INFO, logger="app.main")

    result = asyncio.run(
        main.telegram_webhook(
            SimpleNamespace(json=request_json),
            x_telegram_bot_api_secret_token="expected-secret",
        )
    )

    assert result == {"status": "ok"}
    assert "Telegram webhook received: update_id=123" in caplog.text
    assert "Telegram webhook dispatched successfully: update_id=123" in caplog.text


def test_user_snapshot_allows_missing_telegram_id():
    snapshot = UserSnapshot(
        full_name="External User",
        username=None,
        division="Operations",
        telegram_id=None,
    )

    assert snapshot.telegram_id is None
