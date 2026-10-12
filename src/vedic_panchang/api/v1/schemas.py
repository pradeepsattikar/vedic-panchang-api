"""Public response models (the API data contract). Times are ISO 8601 with UTC offset."""

from datetime import date, datetime

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


class EngineOut(_Model):
    name: str
    library_version: str
    binding_version: str
    ephemeris: str


class CelestialEventOut(_Model):
    status: str = Field(description="occurs | no_event | unavailable")
    time: datetime | None = None
    next_time: datetime | None = Field(
        None, description="For no_event: the next occurrence after this civil date"
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


class DayWindowOut(_Model):
    basis: str = Field(description="sunrise_to_next_sunrise, or civil_day if no sunrise")
    start: datetime
    end: datetime


class SunOut(BaseModel):
    sunrise: CelestialEventOut
    sunset: CelestialEventOut


class MoonOut(BaseModel):
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
