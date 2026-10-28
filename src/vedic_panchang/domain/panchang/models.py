"""Result types for a daily Panchang. All datetimes are timezone-aware, in local time."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from vedic_panchang.domain.panchang.grahas import GrahaPositions
from vedic_panchang.domain.panchang.masa import LunarMonths
from vedic_panchang.domain.panchang.samvatsara import Samvatsara


class EventStatus(StrEnum):
    OCCURS = "occurs"  # the event happens within its window (see DailyPanchang)
    NO_EVENT = "no_event"  # valid outcome: the event does not happen within its window
    UNAVAILABLE = "unavailable"  # cannot be determined, e.g. polar night


@dataclass(frozen=True)
class CelestialEvent:
    status: EventStatus
    time: datetime | None = None
    # When status is NO_EVENT: the next occurrence after the window, if any.
    next_time: datetime | None = None
    reason: str | None = None
    # Moon events only: angular distance between Moon and Sun at the event (degrees).
    moon_sun_separation_deg: float | None = None


@dataclass(frozen=True)
class Span:
    """One occurrence of an element (e.g. a Tithi), with ordered start and end instants."""

    number: int  # 1-based position in its cycle (Tithi 1-30, Nakshatra 1-27, ...)
    id: str
    name: str
    start: datetime
    end: datetime
    paksha: str | None = None


@dataclass(frozen=True)
class Element:
    """A Panchang element over the Panchang day: the value at sunrise plus every span."""

    at_sunrise: Span | None
    spans: tuple[Span, ...]
    unavailable_reason: str | None = None


class PeriodKind(StrEnum):
    AUSPICIOUS = "auspicious"
    INAUSPICIOUS = "inauspicious"


@dataclass(frozen=True)
class TimingInterval:
    id: str
    name: str
    kind: PeriodKind
    start: datetime | None
    end: datetime | None
    applicable: bool
    reason: str | None = None


class DayWindowBasis(StrEnum):
    SUNRISE_TO_NEXT_SUNRISE = "sunrise_to_next_sunrise"
    CIVIL_DAY = "civil_day"  # fallback when there is no sunrise (polar regions)


@dataclass(frozen=True)
class DayWindow:
    basis: DayWindowBasis
    start: datetime
    end: datetime


@dataclass(frozen=True)
class Vara:
    number: int  # 1 = Ravivara (Sunday) ... 7 = Shanivara (Saturday)
    id: str
    name: str


@dataclass(frozen=True)
class YearInfo:
    """Samvat years, Ritu and Ayana at sunrise."""

    vikram_samvat: int  # begins at Chaitra or Kartika Shukla Pratipada (vikram_year_start)
    vikram_year_start: str  # "chaitra" or "kartika", from the profile
    shaka_samvat: int  # Shalivahana Shaka, begins at Chaitra Shukla Pratipada
    # North Indian name (Jupiter cycle, at Mesha Sankranti) of the Chaitradi Vikram year
    vikram_samvatsara: Samvatsara
    shaka_samvatsara: Samvatsara  # Maharashtrian / South Indian name (fixed cycle)
    ritu: str  # Vedic Ritu by lunar month
    ayana: str  # Uttarayana while the Sun is in Makara..Mithuna (sidereal), else Dakshinayana


@dataclass(frozen=True)
class DailyPanchang:
    date: date
    vara: Vara
    masa: LunarMonths  # at sunrise (or at the start of the civil day if no sunrise)
    day_window: DayWindow
    sunrise: CelestialEvent  # within the local civil date
    sunset: CelestialEvent  # within the local civil date
    moonrise: CelestialEvent  # within day_window (sunrise to next sunrise)
    moonset: CelestialEvent  # within day_window
    tithi: Element
    nakshatra: Element
    yoga: Element
    karana: Element
    timings: tuple[TimingInterval, ...]
    sun_sign: Element | None = None  # sidereal Rashi of the Sun, with changes (Sankranti)
    moon_sign: Element | None = None  # sidereal Rashi of the Moon, with changes
    sun_nakshatra: Element | None = None  # the Sun's Nakshatra (Surya Nakshatra), with changes
    year: YearInfo | None = None
    grahas: GrahaPositions | None = None  # the nine grahas at sunrise
    shubh_yogas: tuple = ()  # ShubhYoga windows within the Panchang day (domain/panchang/shubh)
