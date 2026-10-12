"""Conversions between timezone-aware datetimes and Julian days (UT)."""

from datetime import UTC, datetime, timedelta, tzinfo

_UNIX_EPOCH_JD = 2440587.5
_SECONDS_PER_DAY = 86400.0


def to_jd(moment: datetime) -> float:
    if moment.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return moment.timestamp() / _SECONDS_PER_DAY + _UNIX_EPOCH_JD


def from_jd(jd_ut: float, tz: tzinfo) -> datetime:
    """Convert a Julian day to a datetime in ``tz``, rounded to the nearest second."""
    seconds = round((jd_ut - _UNIX_EPOCH_JD) * _SECONDS_PER_DAY)
    return (datetime(1970, 1, 1, tzinfo=UTC) + timedelta(seconds=seconds)).astimezone(tz)
