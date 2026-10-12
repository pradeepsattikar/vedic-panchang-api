import zoneinfo
from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import tzdata

# Always use the IANA database bundled with the `tzdata` package, never the host's copy:
# results must not depend on how up to date the server OS is (e.g. British Columbia's
# move to permanent daylight time in 2026 is missing from older system databases).
zoneinfo.reset_tzpath(to=[])
TIMEZONE_DATA_VERSION: str = tzdata.IANA_VERSION


class InvalidLocationError(ValueError):
    pass


@dataclass(frozen=True)
class Location:
    """A point on Earth plus the IANA timezone used for its civil date and clock times."""

    latitude: float
    longitude: float
    timezone: str
    altitude_m: float = 0.0

    def __post_init__(self) -> None:
        if not -90.0 <= self.latitude <= 90.0:
            raise InvalidLocationError("latitude must be between -90 and 90")
        if not -180.0 <= self.longitude <= 180.0:
            raise InvalidLocationError("longitude must be between -180 and 180")
        if not -500.0 <= self.altitude_m <= 9000.0:
            raise InvalidLocationError("altitude_m must be between -500 and 9000")
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise InvalidLocationError(f"unknown IANA timezone '{self.timezone}'") from None

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)
