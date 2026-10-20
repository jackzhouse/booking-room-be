from datetime import datetime, timezone

from app.core.config import settings


def to_local(dt: datetime) -> datetime:
    """Convert a datetime to the app timezone (Asia/Jakarta).

    MongoDB returns naive datetimes that are stored as UTC, so a naive value is
    read as UTC. Calling astimezone() on it directly would use the server's own
    timezone instead.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(settings.timezone)
