"""Day frames (sunrise, sunset, next sunrise) and kala windows for one location."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from vedic_panchang.astronomy import ephemeris as eph
from vedic_panchang.astronomy.julian import from_jd, to_jd
from vedic_panchang.domain.location import Location
from vedic_panchang.rules.festivals import Kala

_ARUNODAYA_DAYS = 96.0 / 1440.0  # 4 ghatis


@dataclass(frozen=True)
class DayFrame:
    day: date
    sunrise: float
    sunset: float
    next_sunrise: float


class DayFrames:
    """Lazily computed, memoised day frames and moonrises for one location."""

    def __init__(self, location: Location):
        self.location = location
        self.tz = location.tz
        self._frames: dict[date, DayFrame | None] = {}
        self._moonrises: dict[date, float | None] = {}

    def _next(self, body: eph.Body, event: eph.RiseSet, jd: float) -> float | None:
        loc = self.location
        return eph.next_rise_or_set(jd, body, event, loc.longitude, loc.latitude, loc.altitude_m)

    def local_date(self, jd: float) -> date:
        return from_jd(jd, self.tz).date()

    def frame(self, day: date) -> DayFrame | None:
        """None when the Sun does not rise and set on this date (polar regions)."""
        if day not in self._frames:
            self._frames[day] = self._compute(day)
        return self._frames[day]

    def _compute(self, day: date) -> DayFrame | None:
        start = to_jd(datetime.combine(day, time(0), self.tz))
        end = to_jd(datetime.combine(day + timedelta(days=1), time(0), self.tz))
        sunrise = self._next(eph.Body.SUN, eph.RiseSet.RISE, start)
        if sunrise is None or sunrise >= end:
            return None
        sunset = self._next(eph.Body.SUN, eph.RiseSet.SET, sunrise)
        next_sunrise = sunset and self._next(eph.Body.SUN, eph.RiseSet.RISE, sunset)
        if next_sunrise is None or next_sunrise - sunrise > 1.5:
            return None
        return DayFrame(day, sunrise, sunset, next_sunrise)

    def moonrise(self, frame: DayFrame) -> float | None:
        """Moonrise within the Panchang day (sunrise to next sunrise), if any."""
        if frame.day not in self._moonrises:
            jd = self._next(eph.Body.MOON, eph.RiseSet.RISE, frame.sunrise)
            self._moonrises[frame.day] = jd if jd is not None and jd < frame.next_sunrise else None
        return self._moonrises[frame.day]

    def window(self, frame: DayFrame, kala: Kala) -> tuple[float, float] | None:
        """The kala as (start, end) Julian days; instants have start == end."""
        sunrise, sunset, next_sunrise = frame.sunrise, frame.sunset, frame.next_sunrise
        day, night = sunset - sunrise, next_sunrise - sunset
        match kala:
            case Kala.SUNRISE:
                return sunrise, sunrise
            case Kala.SUNSET:
                return sunset, sunset
            case Kala.ARUNODAYA:
                return sunrise - _ARUNODAYA_DAYS, sunrise
            case Kala.PURVAHNA:
                return sunrise, sunrise + day / 2
            case Kala.MADHYAHNA:
                return sunrise + 2 * day / 5, sunrise + 3 * day / 5
            case Kala.APARAHNA:
                return sunrise + 3 * day / 5, sunrise + 4 * day / 5
            case Kala.PRADOSH:
                return sunset, sunset + night / 5
            case Kala.NISHITA:
                return sunset + 7 * night / 15, sunset + 8 * night / 15
            case Kala.MOONRISE:
                moonrise = self.moonrise(frame)
                return None if moonrise is None else (moonrise, moonrise)


def _overlap(a: tuple[float, float], b: tuple[float, float]) -> float:
    return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))


def coverage(
    window: tuple[float, float],
    start: float,
    end: float,
    excluded: list[tuple[float, float]] = (),
) -> float:
    """Fraction of the kala during which [start, end) prevails, ignoring ``excluded``
    periods (which must not overlap each other). Instants score 1 or 0."""
    w_start, w_end = window
    if w_start == w_end:
        inside = start <= w_start < end
        return 1.0 if inside and not any(s <= w_start < e for s, e in excluded) else 0.0
    prevailing = _overlap(window, (start, end))
    for period in excluded:
        clipped = (max(period[0], start), min(period[1], end))
        if clipped[0] < clipped[1]:
            prevailing -= _overlap(window, clipped)
    return max(0.0, prevailing) / (w_end - w_start)
