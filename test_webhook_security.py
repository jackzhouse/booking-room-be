from app.bot.webhook import is_valid_webhook_secret
from app.models.booking import UserSnapshot
from app.core.config import settings


def test_webhook_url_no_longer_embeds_bot_token(monkeypatch):
    monkeypatch.setattr(settings, "WEBHOOK_BASE_URL", "https://example.com")
    monkeypatch.setattr(settings, "BOT_TOKEN", "bot-token-value")

    assert settings.webhook_url == "https://example.com/webhook/telegram"
    assert "bot-token-value" not in settings.webhook_url


def test_webhook_secret_validation(monkeypatch):
    monkeypatch.setattr(settings, "WEBHOOK_SECRET_TOKEN", "super-secret-token")

    assert is_valid_webhook_secret("super-secret-token") is True
    assert is_valid_webhook_secret("wrong-token") is False
    assert is_valid_webhook_secret(None) is False


def test_webhook_secret_optional_for_non_production(monkeypatch):
    monkeypatch.setattr(settings, "WEBHOOK_SECRET_TOKEN", None)

    assert is_valid_webhook_secret(None) is True
    assert is_valid_webhook_secret("anything") is True


def test_user_snapshot_allows_missing_telegram_id():
    snapshot = UserSnapshot(
        full_name="External User",
        username=None,
        division="Operations",
        telegram_id=None,
    )

    assert snapshot.telegram_id is None
