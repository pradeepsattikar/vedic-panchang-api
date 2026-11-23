"""Use cases: daily Panchang, festivals and the city catalogue."""

import calendar
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from functools import lru_cache

from vedic_panchang import __version__
from vedic_panchang.astronomy.ephemeris import ENGINE_INFO, EngineInfo
from vedic_panchang.config import Settings
from vedic_panchang.domain.festivals.engine import FestivalOccurrence, festivals_for_year
from vedic_panchang.domain.location import (
    TIMEZONE_DATA_VERSION,
    InvalidLocationError,
    Location,
)
from vedic_panchang.domain.muhurta.engine import MuhurtaWindow, muhurta_windows
from vedic_panchang.domain.panchang.calculator import calculate_daily_panchang
from vedic_panchang.domain.panchang.models import DailyPanchang
from vedic_panchang.infra.city_repository import City, CityRepository
from vedic_panchang.rules.festivals import FestivalSet, load_festival_set
from vedic_panchang.rules.muhurta import (
    MuhurtaRules,
    Purpose,
    UnknownPurposeError,
    load_muhurta_rules,
)
from vedic_panchang.rules.profiles import (
    CalculationProfile,
    ProfileRegistry,
    UnknownProfileError,
)
from vedic_panchang.rules.shubh import load_shubh_rules

# Errors the API layer maps to responses; re-exported so it depends on services only.
__all__ = [
    "CityNotFoundError",
    "DateOutOfRangeError",
    "FestivalNotFoundError",
    "InvalidLocationError",
    "LocationRequestError",
    "PanchangService",
    "UnknownProfileError",
    "UnknownPurposeError",
]

MAX_MUHURTA_DAYS = 400


class DateOutOfRangeError(ValueError):
    def __init__(self, requested: date | int, min_date: date, max_date: date):
        super().__init__(f"{requested} is outside the supported range {min_date} to {max_date}")
        self.min_date = min_date
        self.max_date = max_date


class CityNotFoundError(LookupError):
    def __init__(self, city_id: str):
        super().__init__(f"No city with id '{city_id}'")
        self.city_id = city_id


class FestivalNotFoundError(LookupError):
    def __init__(self, festival_id: str):
        super().__init__(f"No festival with id '{festival_id}'")


class LocationRequestError(ValueError):
    """Neither a city nor a complete set of coordinates, or both, were given."""


@dataclass(frozen=True)
class Place:
    location: Location
    city: City | None
    request: dict  # how the caller identified the place, echoed back in responses


@dataclass(frozen=True)
class Provenance:
    profile: CalculationProfile
    festival_set: FestivalSet
    engine: EngineInfo
    api_version: str
    shubh_rule_version: str
    timezone_data_version: str
    generated_at: datetime


@dataclass(frozen=True)
class PanchangResult:
    place: Place
    panchang: DailyPanchang
    observances: tuple[FestivalOccurrence, ...]
    provenance: Provenance


@dataclass(frozen=True)
class DaySummary:
    panchang: DailyPanchang
    observances: tuple[FestivalOccurrence, ...]


@dataclass(frozen=True)
class MonthResult:
    place: Place
    year: int
    month: int
    days: tuple[DaySummary, ...]
    provenance: Provenance


@dataclass(frozen=True)
class FestivalsResult:
    place: Place
    year: int
    festivals: tuple[FestivalOccurrence, ...]
    provenance: Provenance


@dataclass(frozen=True)
class MuhurtaResult:
    place: Place
    purpose: Purpose
    rules: MuhurtaRules
    first: date
    last: date
    windows: tuple[MuhurtaWindow, ...]
    provenance: Provenance


class PanchangService:
    engine: EngineInfo = ENGINE_INFO
    api_version: str = __version__
    timezone_data_version: str = TIMEZONE_DATA_VERSION

    def __init__(self, settings: Settings, cities: CityRepository, profiles: ProfileRegistry):
        self.settings = settings
        self.cities = cities
        self.profiles = profiles
        # Pure functions of their arguments; profiles and festival sets carry their rule
        # versions, so cache keys cover date/year + location + rule version.
        self._calculate = lru_cache(maxsize=settings.cache_size)(calculate_daily_panchang)
        self._festivals = lru_cache(maxsize=256)(festivals_for_year)
        self._muhurta_range = lru_cache(maxsize=256)(self._muhurta_for_range)

    # ── locations ────────────────────────────────────────────
    def city(self, city_id: str) -> City:
        city = self.cities.get(city_id)
        if city is None:
            raise CityNotFoundError(city_id)
        return city

    def place(
        self,
        city_id: str | None,
        latitude: float | None,
        longitude: float | None,
        timezone: str | None,
        altitude_m: float = 0.0,
    ) -> Place:
        coordinates = (latitude, longitude, timezone)
        if city_id is not None:
            if any(v is not None for v in coordinates):
                raise LocationRequestError("Give either city_id or lat/lon/tz, not both")
            city = self.city(city_id)
            return Place(city.location, city, {"city_id": city_id})
        if all(v is not None for v in coordinates):
            location = Location(latitude, longitude, timezone, altitude_m)
            request = {"latitude": latitude, "longitude": longitude, "timezone": timezone}
            return Place(location, None, request)
        raise LocationRequestError("Give either city_id, or all of lat, lon and tz")

    # ── use cases ────────────────────────────────────────────
    def daily(self, place: Place, day: date | None, profile_id: str | None) -> PanchangResult:
        profile = self.profiles.get(profile_id)
        # "Today" is the civil date at the requested location, not on the server.
        day = day or datetime.now(place.location.tz).date()
        self._check_date(day)
        festival_set = load_festival_set(profile.festival_set)
        year = self._festivals(day.year, place.location, profile, festival_set)
        return PanchangResult(
            place=place,
            panchang=self._calculate(day, place.location, profile),
            observances=tuple(o for o in year if o.date == day),
            provenance=self._provenance(profile, festival_set),
        )

    def month(
        self, place: Place, year: int | None, month: int | None, profile_id: str | None
    ) -> MonthResult:
        profile = self.profiles.get(profile_id)
        today = datetime.now(place.location.tz).date()
        year, month = year or today.year, month or today.month
        first = date(year, month, 1)
        last = date(year, month, calendar.monthrange(year, month)[1])
        self._check_date(first)
        self._check_date(last)
        festival_set = load_festival_set(profile.festival_set)
        observances = self._festivals(year, place.location, profile, festival_set)
        days = []
        day = first
        while day <= last:
            days.append(
                DaySummary(
                    panchang=self._calculate(day, place.location, profile),
                    observances=tuple(o for o in observances if o.date == day),
                )
            )
            day += timedelta(days=1)
        return MonthResult(place, year, month, tuple(days), self._provenance(profile, festival_set))

    def festivals(
        self,
        place: Place,
        year: int | None,
        profile_id: str | None,
        festival_id: str | None = None,
        category: str | None = None,
    ) -> FestivalsResult:
        profile = self.profiles.get(profile_id)
        year = year or datetime.now(place.location.tz).year
        if not self.settings.min_date.year <= year <= self.settings.max_date.year:
            raise DateOutOfRangeError(year, self.settings.min_date, self.settings.max_date)
        festival_set = load_festival_set(profile.festival_set)
        if festival_id is not None and festival_id not in {
            r.id for r in festival_set.lunar + festival_set.solar
        }:
            raise FestivalNotFoundError(festival_id)
        occurrences = self._festivals(year, place.location, profile, festival_set)
        selected = tuple(
            o
            for o in occurrences
            if (festival_id is None or o.festival_id == festival_id)
            and (category is None or o.category == category)
            and self.settings.min_date <= o.date <= self.settings.max_date
        )
        return FestivalsResult(place, year, selected, self._provenance(profile, festival_set))

    # ── muhurta ──────────────────────────────────────────────
    def muhurta_purposes(self) -> tuple[Purpose, ...]:
        return load_muhurta_rules(self.profiles.get(None).muhurta_set).purposes

    def muhurta(
        self,
        place: Place,
        purpose_id: str,
        first: date | None,
        days: int,
        profile_id: str | None,
    ) -> MuhurtaResult:
        profile = self.profiles.get(profile_id)
        rules = load_muhurta_rules(profile.muhurta_set)
        purpose = rules.purpose(purpose_id)
        first = first or datetime.now(place.location.tz).date()
        last = min(first + timedelta(days=max(1, min(days, MAX_MUHURTA_DAYS)) - 1),
                   self.settings.max_date)  # fmt: skip
        self._check_date(first)
        windows = self._muhurta_range(purpose_id, place.location, first, last, profile)
        festival_set = load_festival_set(profile.festival_set)
        return MuhurtaResult(place, purpose, rules, first, last, windows,
                             self._provenance(profile, festival_set))  # fmt: skip

    @staticmethod
    def _muhurta_for_range(
        purpose_id: str, location: Location, first: date, last: date, profile: CalculationProfile
    ) -> tuple[MuhurtaWindow, ...]:
        """Only the requested days are calculated; the rule version is fixed per deploy."""
        rules = load_muhurta_rules(profile.muhurta_set)
        purpose = rules.purpose(purpose_id)
        return tuple(muhurta_windows(purpose, rules, location, profile.ayanamsha, first, last))

    def _check_date(self, day: date) -> None:
        if not self.settings.min_date <= day <= self.settings.max_date:
            raise DateOutOfRangeError(day, self.settings.min_date, self.settings.max_date)

    def _provenance(self, profile: CalculationProfile, festival_set: FestivalSet) -> Provenance:
        return Provenance(
            profile=profile,
            festival_set=festival_set,
            engine=self.engine,
            api_version=self.api_version,
            shubh_rule_version=load_shubh_rules(profile.shubh_set).rule_version,
            timezone_data_version=self.timezone_data_version,
            generated_at=datetime.now(UTC).replace(microsecond=0),
        )
