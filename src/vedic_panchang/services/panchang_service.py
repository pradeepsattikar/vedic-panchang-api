"""Use cases for daily Panchang and the city catalogue."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from functools import lru_cache

from vedic_panchang import __version__
from vedic_panchang.astronomy.ephemeris import ENGINE_INFO, EngineInfo
from vedic_panchang.config import Settings
from vedic_panchang.domain.location import (
    TIMEZONE_DATA_VERSION,
    InvalidLocationError,
    Location,
)
from vedic_panchang.domain.panchang.calculator import calculate_daily_panchang
from vedic_panchang.domain.panchang.models import DailyPanchang
from vedic_panchang.infra.city_repository import City, CityRepository
from vedic_panchang.rules.profiles import (
    CalculationProfile,
    ProfileRegistry,
    UnknownProfileError,
)

# Errors the API layer maps to responses; re-exported so it depends on services only.
__all__ = [
    "CityNotFoundError",
    "DateOutOfRangeError",
    "InvalidLocationError",
    "PanchangService",
    "UnknownProfileError",
]


class DateOutOfRangeError(ValueError):
    def __init__(self, requested: date, min_date: date, max_date: date):
        super().__init__(
            f"Date {requested} is outside the supported range {min_date} to {max_date}"
        )
        self.min_date = min_date
        self.max_date = max_date


class CityNotFoundError(LookupError):
    def __init__(self, city_id: str):
        super().__init__(f"No city with id '{city_id}'")
        self.city_id = city_id


@dataclass(frozen=True)
class PanchangResult:
    panchang: DailyPanchang
    location: Location
    city: City | None
    profile: CalculationProfile
    engine: EngineInfo
    api_version: str
    timezone_data_version: str
    generated_at: datetime


class PanchangService:
    engine: EngineInfo = ENGINE_INFO
    api_version: str = __version__
    timezone_data_version: str = TIMEZONE_DATA_VERSION

    def __init__(self, settings: Settings, cities: CityRepository, profiles: ProfileRegistry):
        self.settings = settings
        self.cities = cities
        self.profiles = profiles
        # Results are pure functions of (date, location, profile); the profile carries its
        # rule_version, so the cache key covers date + location + rule version.
        self._calculate = lru_cache(maxsize=settings.cache_size)(calculate_daily_panchang)

    def city(self, city_id: str) -> City:
        city = self.cities.get(city_id)
        if city is None:
            raise CityNotFoundError(city_id)
        return city

    def daily_for_city(
        self, city_id: str, day: date | None, profile_id: str | None
    ) -> PanchangResult:
        city = self.city(city_id)
        return self._daily(city.location, city, day, profile_id)

    def daily_for_coordinates(
        self,
        latitude: float,
        longitude: float,
        timezone: str,
        altitude_m: float,
        day: date | None,
        profile_id: str | None,
    ) -> PanchangResult:
        location = Location(latitude, longitude, timezone, altitude_m)
        return self._daily(location, None, day, profile_id)

    def _daily(
        self, location: Location, city: City | None, day: date | None, profile_id: str | None
    ) -> PanchangResult:
        profile = self.profiles.get(profile_id)
        # "Today" is the civil date at the requested location, not on the server.
        day = day or datetime.now(location.tz).date()
        if not self.settings.min_date <= day <= self.settings.max_date:
            raise DateOutOfRangeError(day, self.settings.min_date, self.settings.max_date)
        return PanchangResult(
            panchang=self._calculate(day, location, profile),
            location=location,
            city=city,
            profile=profile,
            engine=self.engine,
            api_version=self.api_version,
            timezone_data_version=self.timezone_data_version,
            generated_at=datetime.now(UTC).replace(microsecond=0),
        )
