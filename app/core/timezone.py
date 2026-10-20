from datetime import date, datetime, time, timedelta, timezone
from typing import Tuple

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


def local_day_bounds_utc(day: date) -> Tuple[datetime, datetime]:
    """Start (inclusive) and end (exclusive) of a local calendar day as naive UTC datetimes.

    Booking times are stored as naive UTC, so a Jakarta day is [00:00, 24:00) WIB
    shifted back to UTC, not the same clock times read as UTC.
    """
    start_local = datetime.combine(day, time.min, tzinfo=settings.timezone)
    end_local = datetime.combine(day + timedelta(days=1), time.min, tzinfo=settings.timezone)
    return (
        start_local.astimezone(timezone.utc).replace(tzinfo=None),
        end_local.astimezone(timezone.utc).replace(tzinfo=None),
    )
