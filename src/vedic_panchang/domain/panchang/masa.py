"""Lunar month (Masa) for both month systems, including Adhika (leap) months.

Amanta months run new moon to new moon and are named after the solar sign (rashi) the
Sun enters during the month: the month in which the Sun enters Mesha is Chaitra. A month
in which the Sun enters no new sign is Adhika and takes the name of the following month.

Purnimanta months run full moon to full moon, so the Krishna paksha carries the name of
the following Amanta month while the Shukla paksha keeps its Amanta name.

Note (D07, pending review): Purnimanta labelling around an Adhika month and the rare
Kshaya month (two sign changes in one month) are provisional.
"""

from collections.abc import Callable
from dataclasses import dataclass

from vedic_panchang.domain.panchang.spans import crossing_near

MASAS = (
    "Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana", "Bhadrapada",
    "Ashwin", "Kartika", "Margashirsha", "Pausha", "Magha", "Phalguna",
)  # fmt: skip

SYNODIC_MONTH_DAYS = 29.530589
_MEAN_ELONGATION_SPEED = 360.0 / SYNODIC_MONTH_DAYS  # degrees per day


@dataclass(frozen=True)
class Masa:
    number: int  # 1 = Chaitra ... 12 = Phalguna
    id: str
    name: str
    is_adhika: bool


@dataclass(frozen=True)
class LunarMonths:
    amanta: Masa
    purnimanta: Masa


def amanta_month_index(sign_at_start: int, sign_at_end: int) -> tuple[int, bool]:
    """(month index 0-11, is_adhika) from the Sun's sidereal sign at the month's two new moons."""
    if sign_at_start == sign_at_end:
        return (sign_at_end + 1) % 12, True
    return sign_at_end, False


def masa(index: int, is_adhika: bool) -> Masa:
    name = MASAS[index]
    prefix = "adhika-" if is_adhika else ""
    return Masa(index + 1, prefix + name.lower(), name, is_adhika)


def _new_moon_before(elongation: Callable[[float], float], jd: float) -> float:
    guess = jd - elongation(jd) / _MEAN_ELONGATION_SPEED
    new_moon = crossing_near(elongation, 0.0, guess, _MEAN_ELONGATION_SPEED)
    if new_moon > jd:
        new_moon = crossing_near(
            elongation, 0.0, new_moon - SYNODIC_MONTH_DAYS, _MEAN_ELONGATION_SPEED
        )
    return new_moon


def _amanta_month(elongation, sun_longitude, jd: float) -> tuple[int, bool, float]:
    """(month index 0-11, is_adhika, end of month JD) for the Amanta month containing jd."""
    start = _new_moon_before(elongation, jd)
    end = crossing_near(elongation, 0.0, start + SYNODIC_MONTH_DAYS, _MEAN_ELONGATION_SPEED)
    index, is_adhika = amanta_month_index(
        int(sun_longitude(start) // 30), int(sun_longitude(end) // 30)
    )
    return index, is_adhika, end


def lunar_months(
    elongation: Callable[[float], float],
    sun_longitude: Callable[[float], float],
    jd: float,
) -> LunarMonths:
    """Lunar months in force at ``jd`` (normally the Panchang day's sunrise)."""
    index, is_adhika, month_end = _amanta_month(elongation, sun_longitude, jd)
    amanta = masa(index, is_adhika)
    if elongation(jd) < 180.0:  # Shukla paksha: both systems agree
        return LunarMonths(amanta, amanta)
    next_index, next_adhika, _ = _amanta_month(elongation, sun_longitude, month_end + 1.0)
    return LunarMonths(amanta, masa(next_index, next_adhika))
