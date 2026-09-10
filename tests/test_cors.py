import pytest

from app.core.cors import build_cors_origins


def test_cors_uses_local_and_current_environment_origins():
    origins = build_cors_origins(
        "https://booking-room-staging.example.com",
        "https://booking-room.example.com/",
    )

    assert origins == [
        "https://booking-room-staging.example.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://booking-room.example.com",
    ]


def test_production_origin_is_preserved_without_staging_origin():
    origins = build_cors_origins(None, "https://booking-room.teknologikartu.com")

    assert "https://booking-room.teknologikartu.com" in origins
    assert "https://booking-room-staging.example.com" not in origins


def test_cors_rejects_wildcard_origin_with_credentials():
    with pytest.raises(ValueError, match="must be explicit"):
        build_cors_origins("*", "https://booking-room.teknologikartu.com")
