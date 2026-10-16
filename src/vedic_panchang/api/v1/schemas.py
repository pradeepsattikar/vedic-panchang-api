"""Public response models (the API data contract). Times are ISO 8601 with UTC offset."""

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class _Model(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CityOut(_Model):
    id: str = Field(description="Stable city ID (GeoNames ID)")
    name: str
    region: str
    country_code: str
    country: str
    latitude: float
    longitude: float
    elevation_m: float
    timezone: str = Field(description="IANA timezone ID")
    population: int


class NearestCityOut(_Model):
    city: CityOut
    distance_km: float


class LocationOut(_Model):
    latitude: float
    longitude: float
    altitude_m: float
    timezone: str


class ProfileOut(_Model):
    id: str
    name: str
    rule_version: str
    ayanamsha: str
    month_system: str
    festival_convention: str
    day_anchor: str
    festival_set: str


class EngineOut(_Model):
    name: str
    library_version: str
    binding_version: str
    ephemeris: str


class CelestialEventOut(_Model):
    status: str = Field(description="occurs | no_event | unavailable")
    time: datetime | None = None
    next_time: datetime | None = Field(
        None, description="For no_event: the next occurrence after the event's window"
    )
    reason: str | None = None
    moon_sun_separation_deg: float | None = Field(
        None, description="Moon events only: Moon-Sun angular distance at the event"
    )


class SpanOut(_Model):
    number: int
    id: str
    name: str
    paksha: str | None = None
    start: datetime
    end: datetime


class ElementOut(_Model):
    at_sunrise: SpanOut | None = Field(description="Day-anchor value: in force at sunrise")
    spans: list[SpanOut] = Field(description="Every span overlapping the Panchang day, in order")
    unavailable_reason: str | None = None


class TimingOut(_Model):
    id: str
    name: str
    kind: str = Field(description="auspicious | inauspicious")
    start: datetime | None
    end: datetime | None
    applicable: bool
    reason: str | None = None


class VaraOut(_Model):
    number: int
    id: str
    name: str


class MasaOut(_Model):
    number: int = Field(description="1 = Chaitra ... 12 = Phalguna")
    id: str
    name: str
    is_adhika: bool


class LunarMonthsOut(_Model):
    amanta: MasaOut
    purnimanta: MasaOut


class PujaTimeOut(_Model):
    id: str = Field(
        description="Muhurta id, e.g. pradosh, madhyahna, nishita, lakshmi_puja, parana, "
        "rakhi, holika_dahan, moonrise. Labels are the client's (i18n)."
    )
    start: datetime
    end: datetime = Field(description="Equal to start for an instant (moonrise, sunset)")


class FestivalOut(_Model):
    festival_id: str
    occurrence_id: str = Field(description="Stable across locations")
    name: str
    short_name: str = Field(description="Label for tight spaces such as calendar cells")
    category: str = Field(description="major | observance")
    date: Annotated[date, Field(description="Local civil date of observance at this place")]
    kala: str | None = Field(
        description="Part of the day in which the Tithi must prevail (lunar festivals)"
    )
    tithi: SpanOut | None = Field(None, description="The Tithi with local start and end")
    masa: LunarMonthsOut | None = None
    sankranti_time: datetime | None = Field(None, description="Solar festivals: Sun's ingress")
    puja_times: list[PujaTimeOut] = Field(
        default_factory=list,
        description="Customary puja / observance times, most important first. Empty when the "
        "tradition prescribes no particular time. Parana is on the day after the date.",
    )


class DayWindowOut(_Model):
    basis: str = Field(description="sunrise_to_next_sunrise, or civil_day if no sunrise")
    start: datetime
    end: datetime


class SunOut(BaseModel):
    """Sunrise and sunset on the local civil date."""

    sunrise: CelestialEventOut
    sunset: CelestialEventOut


class MoonOut(BaseModel):
    """Moonrise and moonset within the Panchang day (sunrise to next sunrise)."""

    moonrise: CelestialEventOut
    moonset: CelestialEventOut


class RequestContextOut(BaseModel):
    date: date
    city_id: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None
    profile: str


class DailyPanchangOut(BaseModel):
    request: RequestContextOut
    date: date
    location: LocationOut
    city: CityOut | None
    profile: ProfileOut
    engine: EngineOut
    api_version: str
    timezone_data_version: str = Field(description="IANA tz database version used")
    generated_at: datetime
    vara: VaraOut
    masa: LunarMonthsOut = Field(description="Lunar month at sunrise in both systems")
    day_window: DayWindowOut
    sun: SunOut
    moon: MoonOut
    tithi: ElementOut
    nakshatra: ElementOut
    yoga: ElementOut
    karana: ElementOut
    timings: list[TimingOut]
    observances: list[FestivalOut] = Field(description="Festivals and observances on this date")
    festival_rule_version: str


class MonthDayOut(BaseModel):
    """Compact day summary for calendar views; use /panchang/daily for full detail."""

    date: date
    vara: VaraOut
    masa: LunarMonthsOut
    sunrise: CelestialEventOut
    sunset: CelestialEventOut
    tithi_at_sunrise: SpanOut | None
    nakshatra_at_sunrise: SpanOut | None
    observances: list[FestivalOut]


class MonthRequestOut(BaseModel):
    year: int
    month: int
    city_id: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None
    profile: str


class MonthOut(BaseModel):
    request: MonthRequestOut
    year: int
    month: int
    location: LocationOut
    city: CityOut | None
    profile: ProfileOut
    festival_rule_version: str
    engine: EngineOut
    api_version: str
    timezone_data_version: str
    generated_at: datetime
    days: list[MonthDayOut]


class FestivalsRequestOut(BaseModel):
    year: int
    city_id: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None
    profile: str
    festival_id: str | None = None
    category: str | None = None


class FestivalsOut(BaseModel):
    request: FestivalsRequestOut
    year: int
    location: LocationOut
    city: CityOut | None
    profile: ProfileOut
    festival_rule_version: str
    engine: EngineOut
    api_version: str
    timezone_data_version: str
    generated_at: datetime
    festivals: list[FestivalOut]


class DateRangeOut(BaseModel):
    min_date: date
    max_date: date


class CatalogueOut(BaseModel):
    city_count: int
    countries: list[str]
    attribution: str


class MetaOut(BaseModel):
    api_version: str
    engine: EngineOut
    timezone_data_version: str
    default_profile: str
    profiles: list[ProfileOut]
    supported_dates: DateRangeOut
    city_catalogue: CatalogueOut
    source_code: str
    license: str


class ErrorDetailOut(BaseModel):
    code: str
    message: str
    details: dict | None = None


class ErrorOut(BaseModel):
    error: ErrorDetailOut
    request: dict = Field(description="The request parameters, preserved for context")
