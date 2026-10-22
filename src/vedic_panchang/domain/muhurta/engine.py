"""General muhurtas (Panchang Shuddhi) for a purpose, e.g. Vivah or Griha Pravesh.

The Panchang days of the requested dates are cut into pieces at every boundary that can change
the verdict (Tithi, Nakshatra, Gandanta pada, Yoga, Bhadra, the Sun's sign, sunrise, lunar month,
Chaturmas, Guru/Shukra asta). Each piece is judged by the purpose's rules at its midpoint, and
consecutive good pieces within a Panchang day are joined into a window. Windows shorter than the
rule set's minimum are dropped. Nothing about a person (birth chart, Lagna) is considered.
"""

import bisect
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from functools import cache

from vedic_panchang.astronomy import ephemeris as eph
from vedic_panchang.astronomy.julian import from_jd, to_jd
from vedic_panchang.domain.festivals.calendar import TithiInstance, bhadra_periods, lunar_year
from vedic_panchang.domain.festivals.kala import DayFrame, DayFrames
from vedic_panchang.domain.location import Location
from vedic_panchang.domain.panchang import names
from vedic_panchang.domain.panchang.spans import spans_over
from vedic_panchang.rules.muhurta import MuhurtaRules, Purpose

NAK_DEG = 360.0 / 27.0
PADA_DEG = NAK_DEG / 4.0
YOGA_DEG = 360.0 / 27.0
_DAY_DEG = 360.0  # kalamsha: one day of time = 360 degrees (4 minutes = 1 degree)

# Gandanta: the first pada of Ashwini, Magha and Mula; the last pada of Revati, Ashlesha, Jyeshtha.
_GANDANTA_START = {0, 9, 18}
_GANDANTA_END = {26, 8, 17}
_ASHADHA, _KARTIKA = 3, 7


# Angle boundaries that are the same for every city: (angle from sidereal Sun and Moon,
# segment size, search horizon in days). Bhadra is handled separately.
_GLOBAL_ANGLES = {
    "tithi": (lambda sun, moon: (moon - sun) % 360.0, 12.0, 2.0),
    "nakshatra": (lambda sun, moon: moon, NAK_DEG, 2.0),
    "pada": (lambda sun, moon: moon, PADA_DEG, 2.0),
    "yoga": (lambda sun, moon: (sun + moon) % 360.0, YOGA_DEG, 2.0),
    "sun_sign": (lambda sun, moon: sun, 30.0, 33.0),
}


@cache
def _year_boundaries(kind: str, year: int, ayanamsha: eph.Ayanamsha) -> tuple[float, ...]:
    """Every boundary of one kind around a calendar year (UT), worked out once and shared by all
    cities and requests: only sunrise-based parts of a muhurta depend on the place."""
    lo = to_jd(datetime(year, 1, 1, tzinfo=UTC)) - 3.0
    hi = to_jd(datetime(year + 1, 1, 1, tzinfo=UTC)) + 3.0
    if kind == "bhadra":
        return tuple(jd for period in bhadra_periods(ayanamsha, lo, hi) for jd in period)
    angle_of, segment, search_days = _GLOBAL_ANGLES[kind]

    def angle(jd: float) -> float:
        return angle_of(*eph.sidereal_sun_moon(jd, ayanamsha))

    spans = spans_over(angle, segment, lo, hi, search_days=search_days)
    return tuple(sorted({jd for span in spans for jd in (span.start_jd, span.end_jd)}))


def _boundaries(kind: str, lo: float, hi: float, ayanamsha: eph.Ayanamsha) -> list[float]:
    years = range(from_jd(lo, UTC).year, from_jd(hi, UTC).year + 1)
    return [jd for y in years for jd in _year_boundaries(kind, y, ayanamsha) if lo <= jd <= hi]


@dataclass(frozen=True)
class MuhurtaWindow:
    day: date  # civil date of the Panchang day's sunrise
    start: datetime
    end: datetime
    nakshatras: tuple[str, ...]
    tithis: tuple[str, ...]


class _Sky:
    """Sidereal Sun and Moon at an instant, and the Panchang elements derived from them."""

    def __init__(self, jd: float, ayanamsha: eph.Ayanamsha):
        self.sun, self.moon = eph.sidereal_sun_moon(jd, ayanamsha)
        elongation = (self.moon - self.sun) % 360.0
        self.tithi = int(elongation // 12.0) + 1  # 1-30
        self.karana = names.karana_name(int(elongation // 6.0))
        self.nakshatra = int(self.moon // NAK_DEG)  # 0-26
        into = self.moon % NAK_DEG
        self.gandanta = (self.nakshatra in _GANDANTA_START and into < PADA_DEG) or (
            self.nakshatra in _GANDANTA_END and into >= NAK_DEG - PADA_DEG
        )
        self.yoga = int(((self.sun + self.moon) % 360.0) // YOGA_DEG)
        self.sun_sign = int(self.sun // 30.0)


class _LunarMonths:
    """Amanta month (and Adhika flag) at any instant, from the global Tithi calendar."""

    def __init__(self, instances: list[TithiInstance]):
        self.instances = sorted(instances, key=lambda i: i.start_jd)
        self.starts = [i.start_jd for i in self.instances]

    def at(self, jd: float) -> TithiInstance:
        return self.instances[max(bisect.bisect_right(self.starts, jd) - 1, 0)]

    def chaturmas(self) -> list[tuple[float, float]]:
        """From the start of Ashadha Shukla Ekadashi to the end of Kartika Shukla Ekadashi."""
        starts = [
            i.start_jd
            for i in self.instances
            if i.number == 11 and i.month.index == _ASHADHA and not i.month.is_adhika
        ]
        ends = [
            i.end_jd
            for i in self.instances
            if i.number == 11 and i.month.index == _KARTIKA and not i.month.is_adhika
        ]
        out = []
        for start in starts:
            later = [e for e in ends if e > start]
            if later:
                out.append((start, min(later)))
        return out


class _Asta:
    """Whether a planet is asta (combust), judged once a day by its kalamsha at the place."""

    def __init__(self, body: eph.Body, limit: float, inferior_limit: float | None,
                 frames: DayFrames, days: list[DayFrame]):  # fmt: skip
        self.events: list[float] = []
        self.states: list[bool] = []
        loc = frames.location
        where = (loc.longitude, loc.latitude, loc.altitude_m)
        for frame in days:
            sun = eph.planet_position(frame.sunset, eph.Body.SUN)
            planet = eph.planet_position(frame.sunset, body)
            evening = (planet.longitude - sun.longitude) % 360.0 < 180.0
            # Sun and planet measured alike: centre of the disc, no refraction.
            if evening:  # sets after the Sun: compare settings
                s_set = eph.geometric_rise_or_set(
                    frame.sunrise, eph.Body.SUN, eph.RiseSet.SET, *where
                )
                p_set = s_set and eph.geometric_rise_or_set(
                    s_set - 0.4, body, eph.RiseSet.SET, *where
                )
                gap = None if not p_set else (p_set - s_set) * _DAY_DEG
                event = frame.sunset
            else:  # rises before the Sun: compare risings
                s_rise = eph.geometric_rise_or_set(
                    frame.sunrise - 0.3, eph.Body.SUN, eph.RiseSet.RISE, *where
                )
                p_rise = s_rise and eph.geometric_rise_or_set(
                    s_rise - 0.6, body, eph.RiseSet.RISE, *where
                )
                gap = None if not p_rise else (s_rise - p_rise) * _DAY_DEG
                event = frame.sunrise
            near_inferior = (inferior_limit is not None and evening
                             and planet.distance_au < sun.distance_au)  # fmt: skip
            threshold = inferior_limit if near_inferior else limit
            self.events.append(event)
            self.states.append(gap is None or gap < threshold)
        order = sorted(range(len(self.events)), key=self.events.__getitem__)
        self.events = [self.events[i] for i in order]
        self.states = [self.states[i] for i in order]

    def at(self, jd: float) -> bool:
        i = bisect.bisect_right(self.events, jd) - 1
        return self.states[i] if i >= 0 else self.states[0]


def muhurta_windows(
    purpose: Purpose,
    rules: MuhurtaRules,
    location: Location,
    ayanamsha: eph.Ayanamsha,
    first: date,
    last: date,
) -> list[MuhurtaWindow]:
    """Muhurta windows on the Panchang days from ``first`` to ``last`` (inclusive)."""
    frames = DayFrames(location)
    days = []
    day = first
    while day <= last:
        frame = frames.frame(day)
        if frame is not None:  # polar day/night: no Panchang day, no muhurta
            days.append(frame)
        day += timedelta(days=1)
    if not days:
        return []
    lo, hi = days[0].sunrise, days[-1].next_sunrise

    cuts: set[float] = set()
    cuts.update(_boundaries("tithi", lo, hi, ayanamsha))
    cuts.update(_boundaries("pada" if purpose.avoid_gandanta else "nakshatra", lo, hi, ayanamsha))
    if purpose.yogas_excluded:
        cuts.update(_boundaries("yoga", lo, hi, ayanamsha))
    if purpose.solar_months_excluded:
        cuts.update(_boundaries("sun_sign", lo, hi, ayanamsha))
    if purpose.avoid_bhadra:
        cuts.update(_boundaries("bhadra", lo, hi, ayanamsha))

    years = range(first.year, last.year + 1)
    months = _LunarMonths([i for y in years for i in lunar_year(y, ayanamsha)])
    chaturmas = months.chaturmas() if purpose.avoid_chaturmas else []
    for start, end in chaturmas:
        cuts.update((start, end))

    asta: list[_Asta] = []
    margin = [f for f in (frames.frame(first - timedelta(days=1)),) if f is not None]
    for planet in purpose.asta:
        if planet == "jupiter":
            tracker = _Asta(eph.Body.JUPITER, rules.asta.jupiter, None, frames, margin + days)
        else:
            limits = (rules.asta.venus, rules.asta.venus_near_inferior_conjunction)
            tracker = _Asta(eph.Body.VENUS, *limits, frames, margin + days)
        asta.append(tracker)
        cuts.update(tracker.events)
    for frame in days:
        cuts.update((frame.sunrise, frame.next_sunrise))

    edges = sorted(c for c in cuts if lo <= c <= hi)
    windows: list[MuhurtaWindow] = []
    frame_index = 0
    current: dict | None = None

    def close() -> None:
        nonlocal current
        if current and (current["end"] - current["start"]) * 1440.0 >= rules.min_minutes:
            windows.append(MuhurtaWindow(
                day=current["day"],
                start=from_jd(current["start"], location.tz),
                end=from_jd(current["end"], location.tz),
                nakshatras=tuple(current["naks"]),
                tithis=tuple(current["tithis"]),
            ))  # fmt: skip
        current = None

    for a, b in zip(edges, edges[1:], strict=False):
        if b - a < 1e-9:
            continue
        while frame_index + 1 < len(days) and days[frame_index].next_sunrise <= a:
            frame_index += 1
        frame = days[frame_index]
        if current and current["day"] != frame.day:
            close()
        mid = (a + b) / 2.0
        sky = _Sky(mid, ayanamsha)
        month = months.at(mid).month
        good = (
            names.slug(names.NAKSHATRAS[sky.nakshatra]) in purpose.nakshatras
            and sky.tithi in purpose.tithis
            and frame.day.weekday() not in purpose.weekdays_excluded
            and not month.is_adhika
            and (purpose.lunar_months is None or month.index in purpose.lunar_months)
            and sky.sun_sign not in purpose.solar_months_excluded
            and names.slug(names.YOGAS[sky.yoga]) not in purpose.yogas_excluded
            and not (purpose.avoid_bhadra and sky.karana == "Vishti")
            and not (purpose.avoid_gandanta and sky.gandanta)
            and not any(s <= mid < e for s, e in chaturmas)
            and not any(tracker.at(mid) for tracker in asta)
        )
        if not good:
            close()
            continue
        if current is None:
            current = {"day": frame.day, "start": a, "end": b, "naks": [], "tithis": []}
        current["end"] = b
        nak = names.NAKSHATRAS[sky.nakshatra]
        tithi = names.TITHIS[sky.tithi - 1]
        if nak not in current["naks"]:
            current["naks"].append(nak)
        if tithi not in current["tithis"]:
            current["tithis"].append(tithi)
    close()
    return windows
