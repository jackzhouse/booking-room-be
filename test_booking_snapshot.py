from app.models.booking import UserSnapshot


def test_user_snapshot_includes_external_user_id_and_optional_telegram_id():
    snapshot = UserSnapshot(
        full_name="Katalis User",
        username="katalis.user",
        division="Operations",
        telegram_id=None,
        telegram_username="katalisbot",
        external_user_id="ext-123",
    )

    assert snapshot.telegram_id is None
    assert snapshot.telegram_username == "katalisbot"
    assert snapshot.external_user_id == "ext-123"


def test_user_snapshot_defaults_missing_external_user_id_to_none():
    snapshot = UserSnapshot(
        full_name="Telegram User",
        username="tg.user",
        division="Engineering",
        telegram_id=123456789,
    )

    assert snapshot.telegram_id == 123456789
    assert snapshot.telegram_username is None
    assert snapshot.external_user_id is None
