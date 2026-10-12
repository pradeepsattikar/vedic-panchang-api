"""Daily timing intervals derived from sunrise and sunset (D08 formulae)."""

from collections.abc import Callable
from datetime import datetime

from vedic_panchang.domain.panchang.models import PeriodKind, TimingInterval
from vedic_panchang.rules.profiles import CalculationProfile

ToLocal = Callable[[float], datetime]

_DAY_PERIOD_NAMES = {
    "rahu_kalam": "Rahu Kalam",
    "yamaganda": "Yamaganda",
    "gulika_kalam": "Gulika Kalam",
}
_MINUTES_PER_DAY = 1440.0
_WEEKDAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def _interval(id_, name, kind, start_jd, end_jd, to_local: ToLocal) -> TimingInterval:
    return TimingInterval(id_, name, kind, to_local(start_jd), to_local(end_jd), applicable=True)


def _unavailable(id_, name, kind, reason) -> TimingInterval:
    return TimingInterval(id_, name, kind, None, None, applicable=False, reason=reason)


def day_timings(
    sunrise_jd: float | None,
    sunset_jd: float | None,
    weekday: int,
    profile: CalculationProfile,
    to_local: ToLocal,
) -> tuple[TimingInterval, ...]:
    periods = [
        (pid, _DAY_PERIOD_NAMES[pid], PeriodKind.INAUSPICIOUS) for pid, _ in profile.day_periods
    ]
    muhurtas = [
        ("abhijit_muhurta", "Abhijit Muhurta", PeriodKind.AUSPICIOUS),
        ("brahma_muhurta", "Brahma Muhurta", PeriodKind.AUSPICIOUS),
    ]

    if sunrise_jd is None or sunset_jd is None:
        reason = "Requires both sunrise and sunset on this date at this location"
        return tuple(_unavailable(*p, reason) for p in periods + muhurtas)

    day_length = sunset_jd - sunrise_jd
    results = []

    # Inauspicious periods: the daytime split into 8 equal parts.
    eighth = day_length / 8.0
    for pid, name, kind in periods:
        part = profile.day_part(pid, weekday)
        start = sunrise_jd + (part - 1) * eighth
        results.append(_interval(pid, name, kind, start, start + eighth, to_local))

    # Abhijit Muhurta: the 8th of the 15 daytime muhurtas.
    muhurta = day_length / 15.0
    abhijit_start = sunrise_jd + 7 * muhurta
    if weekday in profile.abhijit_excluded_weekdays:
        results.append(
            _unavailable(
                "abhijit_muhurta",
                "Abhijit Muhurta",
                PeriodKind.AUSPICIOUS,
                f"Abhijit Muhurta is avoided on {_WEEKDAY_NAMES[weekday]}s",
            )
        )
    else:
        results.append(
            _interval(
                "abhijit_muhurta",
                "Abhijit Muhurta",
                PeriodKind.AUSPICIOUS,
                abhijit_start,
                abhijit_start + muhurta,
                to_local,
            )
        )

    # Brahma Muhurta: the 14th of the 15 night muhurtas, i.e. two night muhurtas before
    # sunrise to one night muhurta before sunrise. Night length = 24 h minus day length.
    night_muhurta = (_MINUTES_PER_DAY - day_length * _MINUTES_PER_DAY) / 15.0 / _MINUTES_PER_DAY
    results.append(
        _interval(
            "brahma_muhurta",
            "Brahma Muhurta",
            PeriodKind.AUSPICIOUS,
            sunrise_jd - 2 * night_muhurta,
            sunrise_jd - night_muhurta,
            to_local,
        )
    )
    return tuple(results)
