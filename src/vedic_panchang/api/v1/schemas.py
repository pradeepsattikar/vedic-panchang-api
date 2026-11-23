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
    vikram_year_start: str


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
    sade_teen_muhurat: str | None = Field(
        None, description="'full' or 'half' on the Sade Teen (3 1/2) Muhurat days, else null"
    )


class ShubhYogaOut(_Model):
    id: str = Field(description="guru-pushya, ravi-pushya, amrit-siddhi, sarvartha-siddhi, ...")
    name: str
    how: str = Field(description="How the combination is formed, in plain English")
    note: str | None = Field(None, description="Traditional meaning, where one is customary")
    special: bool = Field(description="Rare and widely observed (starred on calendars)")
    start: datetime
    end: datetime


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


class SamvatsaraOut(_Model):
    number: int = Field(description="1 = Prabhava ... 60 = Akshaya")
    id: str
    name: str


class YearInfoOut(_Model):
    vikram_samvat: int = Field(
        description="Begins at Chaitra Shukla Pratipada, or at Kartika Shukla Pratipada (the day "
        "after Diwali) when vikram_year_start is 'kartika'"
    )
    vikram_year_start: str = Field(description="'chaitra' (North India) or 'kartika' (Maharashtra)")
    shaka_samvat: int = Field(description="Shalivahana Shaka; begins at Chaitra Shukla Pratipada")
    vikram_samvatsara: SamvatsaraOut = Field(
        description="North Indian year name: Jupiter (Barhaspatya) cycle at Mesha Sankranti, "
        "for the Chaitradi Vikram year"
    )
    shaka_samvatsara: SamvatsaraOut = Field(
        description="Maharashtrian / South Indian year name: fixed cycle on the Shaka year"
    )
    ritu: str = Field(description="Vedic Ritu by lunar month")
    ayana: str = Field(description="Uttarayana (Sun in Makara..Mithuna, sidereal) or Dakshinayana")


class GrahaOut(_Model):
    id: str = Field(description="surya, chandra, mangal, budha, guru, shukra, shani, rahu, ketu")
    name: str = Field(description="Sanskrit name")
    english: str
    longitude: float = Field(description="Sidereal (Lahiri) longitude, degrees 0-360")
    rashi_number: int = Field(description="1 = Mesha ... 12 = Meena")
    rashi: str
    degree_in_rashi: float = Field(description="Degrees within the Rashi, 0-30")
    nakshatra_number: int = Field(description="1 = Ashwini ... 27 = Revati")
    nakshatra: str
    pada: int = Field(description="Quarter of the Nakshatra, 1-4")
    retrograde: bool = Field(description="Vakri: the longitude is decreasing")


class GrahaPositionsOut(_Model):
    at: datetime = Field(description="Instant of the positions: sunrise of the Panchang day")
    lunar_node: str = Field(description="Rahu/Ketu from the 'mean' or 'true' lunar node")
    grahas: list[GrahaOut]


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
    year: YearInfoOut | None = Field(None, description="Samvat years, Ritu and Ayana at sunrise")
    day_window: DayWindowOut
    sun: SunOut
    moon: MoonOut
    tithi: ElementOut
    nakshatra: ElementOut
    yoga: ElementOut
    karana: ElementOut
    sun_sign: ElementOut | None = Field(None, description="Sidereal Rashi of the Sun, with changes")
    moon_sign: ElementOut | None = Field(
        None, description="Sidereal Rashi of the Moon, with changes"
    )
    sun_nakshatra: ElementOut | None = Field(
        None, description="The Sun's Nakshatra (Surya Nakshatra), with changes"
    )
    grahas: GrahaPositionsOut | None = Field(
        None, description="Positions of the nine grahas at sunrise (facts only)"
    )
    shubh_yogas: list[ShubhYogaOut] = Field(
        default_factory=list,
        description="Auspicious weekday/Nakshatra/Tithi combinations within the Panchang day",
    )
    shubh_rule_version: str | None = None
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
    shubh_yogas: list[ShubhYogaOut] = Field(default_factory=list)


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
    shubh_rule_version: str | None = None
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


class MuhurtaPurposeOut(_Model):
    id: str
    name: str
    description: str


class MuhurtaWindowOut(_Model):
    day: date = Field(description="Civil date of the Panchang day (sunrise to next sunrise)")
    start: datetime
    end: datetime
    nakshatras: list[str] = Field(description="Nakshatras during the window, in order")
    tithis: list[str] = Field(description="Tithis during the window, in order")


class MuhurtaRequestOut(BaseModel):
    city_id: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None
    purpose: str
    from_date: date
    days: int
    profile: str


class MuhurtaOut(BaseModel):
    request: MuhurtaRequestOut
    purpose: MuhurtaPurposeOut
    from_date: date
    to_date: date
    location: LocationOut
    city: CityOut | None
    profile: ProfileOut
    engine: EngineOut
    api_version: str
    timezone_data_version: str
    muhurta_rule_version: str
    basis: str = Field(
        description="What the windows are based on: general Panchang Shuddhi only; not a "
        "personal birth chart or Lagna Shuddhi"
    )
    generated_at: datetime
    windows: list[MuhurtaWindowOut]
