"""Location-independent lunar and solar calendar for a Gregorian year.

Tithi boundaries, new moons and Sankrantis are global instants: they happen at the same
moment everywhere. They are computed once per (year, ayanamsha) and cached; only the
choice of civil day (see engine.py) depends on the location.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache

from vedic_panchang.astronomy import ephemeris as eph
from vedic_panchang.astronomy.julian import to_jd
from vedic_panchang.domain.panchang.masa import LunarMonths, amanta_month_index, masa
from vedic_panchang.domain.panchang.names import karana_name
from vedic_panchang.domain.panchang.spans import crossing_near, spans_over

# Margin around the year so that festivals near 1 January / 31 December, and the months
# containing them, are complete.
_MARGIN_DAYS = 45.0
_SUN_MEAN_SPEED = 0.9856  # degrees per day


@dataclass(frozen=True)
class AmantaMonth:
    index: int  # 0 = Chaitra ... 11 = Phalguna
    is_adhika: bool
    start_jd: float  # new moon
    end_jd: float  # next new moon


@dataclass(frozen=True)
class TithiInstance:
    number: int  # 1-30
    start_jd: float
    end_jd: float
    month: AmantaMonth
    months: LunarMonths  # display names in both month systems


@dataclass(frozen=True)
class Sankranti:
    sign: int  # 0 = Mesha ... 11 = Meena
    jd: float


def _year_bounds(year: int) -> tuple[float, float]:
    start = to_jd(datetime(year, 1, 1, tzinfo=UTC)) - _MARGIN_DAYS
    end = to_jd(datetime(year + 1, 1, 1, tzinfo=UTC)) + _MARGIN_DAYS
    return start, end


@cache
def lunar_year(year: int, ayanamsha: eph.Ayanamsha) -> tuple[TithiInstance, ...]:
    """Every complete Tithi in (and around) the year, tagged with its lunar month."""

    def elongation(jd: float) -> float:
        sun, moon = eph.sidereal_sun_moon(jd, ayanamsha)
        return (moon - sun) % 360.0

    def sun_longitude(jd: float) -> float:
        return eph.sidereal_sun_moon(jd, ayanamsha)[0]

    start, end = _year_bounds(year)
    raw = spans_over(elongation, 12.0, start, end)

    # Months run between consecutive new moons, i.e. the starts of Tithi 1.
    new_moons = [r.start_jd for r in raw if r.index == 0]
    months = []
    for month_start, month_end in zip(new_moons, new_moons[1:], strict=False):
        index, is_adhika = amanta_month_index(
            int(sun_longitude(month_start) // 30), int(sun_longitude(month_end) // 30)
        )
        months.append(AmantaMonth(index, is_adhika, month_start, month_end))

    instances = []
    for position, month in enumerate(months):
        following = months[position + 1] if position + 1 < len(months) else None
        amanta = masa(month.index, month.is_adhika)
        for r in raw:
            if not month.start_jd <= r.start_jd < month.end_jd:
                continue
            if r.index < 15 or following is None:
                purnimanta = amanta
            else:  # Krishna paksha carries the following month's name
                purnimanta = masa(following.index, following.is_adhika)
            instances.append(
                TithiInstance(
                    r.index + 1, r.start_jd, r.end_jd, month, LunarMonths(amanta, purnimanta)
                )
            )
    return tuple(instances)


@cache
def sankrantis(year: int, ayanamsha: eph.Ayanamsha) -> tuple[Sankranti, ...]:
    """The Sun's entries into each sidereal sign in (and around) the year."""

    def sun_longitude(jd: float) -> float:
        return eph.sidereal_sun_moon(jd, ayanamsha)[0]

    start, end = _year_bounds(year)
    result = []
    sign = int(sun_longitude(start) // 30)
    jd = start
    while True:
        sign = (sign + 1) % 12
        degrees_to_go = (sign * 30.0 - sun_longitude(jd)) % 360.0
        jd = crossing_near(sun_longitude, sign * 30.0, jd + degrees_to_go / _SUN_MEAN_SPEED,
                           _SUN_MEAN_SPEED)  # fmt: skip
        if jd > end:
            return tuple(result)
        result.append(Sankranti(sign, jd))


def bhadra_periods(ayanamsha: eph.Ayanamsha, start: float, end: float) -> list[tuple[float, float]]:
    """Bhadra (Vishti karana) intervals overlapping [start, end)."""

    def elongation(jd: float) -> float:
        sun, moon = eph.sidereal_sun_moon(jd, ayanamsha)
        return (moon - sun) % 360.0

    return [
        (r.start_jd, r.end_jd)
        for r in spans_over(elongation, 6.0, start, end)
        if karana_name(r.index) == "Vishti"
    ]
