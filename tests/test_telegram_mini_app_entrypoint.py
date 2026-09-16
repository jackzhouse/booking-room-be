from app.core.config import Settings


def test_mini_app_url_defaults_to_frontend_telegram_route():
    settings = Settings(
        APP_ENV="development",
        FRONTEND_URL="https://booking.test/",
    )

    assert settings.telegram_mini_app_url == "https://booking.test/telegram"


def test_mini_app_url_can_be_explicitly_configured():
    settings = Settings(
        APP_ENV="development",
        FRONTEND_URL="https://booking.test",
        TELEGRAM_MINI_APP_URL="https://mini.booking.test/app",
    )

    assert settings.telegram_mini_app_url == "https://mini.booking.test/app"
