"""Assign festivals and observances to local civil dates.

For a lunar rule, the festival falls on the civil day on which its Tithi prevails during
the rule's kala (e.g. Pradosh for Diwali); time under Bhadra does not count for rules that
avoid it. If the Tithi prevails in the kala on two days, the rule's tie-break decides. If
on neither, the day on which the Tithi prevails at sunrise is used (udaya tithi), and for a
Tithi that touches no sunrise, the Panchang day in which it begins.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from vedic_panchang.astronomy.julian import from_jd
from vedic_panchang.domain.festivals.calendar import (
    Sankranti,
    TithiInstance,
    bhadra_periods,
    lunar_year,
    sankrantis,
)
from vedic_panchang.domain.festivals.kala import DayFrames, coverage
from vedic_panchang.domain.location import Location
from vedic_panchang.domain.panchang import names
from vedic_panchang.domain.panchang.masa import LunarMonths
from vedic_panchang.domain.panchang.models import Span
from vedic_panchang.rules.festivals import (
    SIGN_IDS,
    AdhikaPolicy,
    Category,
    FestivalSet,
    LunarRule,
    SolarRule,
    TieBreak,
)
from vedic_panchang.rules.profiles import CalculationProfile

SIGN_NAMES = (
    "Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
    "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena",
)  # fmt: skip


@dataclass(frozen=True)
class FestivalOccurrence:
    festival_id: str
    occurrence_id: str  # stable across locations (derived from a global instant)
    name: str
    short_name: str  # label for tight spaces such as calendar cells
    category: Category
    date: date  # local civil date of observance
    kala: str | None  # lunar rules: the part of day the Tithi must prevail in
    tithi: Span | None = None  # lunar rules: the Tithi with local start/end
    masa: LunarMonths | None = None
    sankranti_time: datetime | None = None  # solar rules


def _matches(rule: LunarRule, inst: TithiInstance) -> bool:
    if inst.number != rule.tithi:
        return False
    month = inst.month
    if rule.adhika is AdhikaPolicy.NEVER and month.is_adhika:
        return False
    if rule.adhika is AdhikaPolicy.ONLY and not month.is_adhika:
        return False
    if rule.amanta_month is not None and month.index != rule.amanta_month:
        return False
    return month.index not in rule.skip_amanta_months or month.is_adhika


def _choose_day(rule: LunarRule, inst: TithiInstance, frames: DayFrames, ayanamsha) -> date | None:
    first = frames.local_date(inst.start_jd) - timedelta(days=1)
    last = frames.local_date(inst.end_jd) + timedelta(days=1)
    bhadra = (
        bhadra_periods(ayanamsha, inst.start_jd - 1.0, inst.end_jd + 1.0)
        if rule.avoid_bhadra
        else []
    )
    scored: list[tuple[date, float]] = []
    udaya: date | None = None  # first day on which the Tithi prevails at sunrise
    home: date | None = None  # Panchang day in which the Tithi begins
    day = first
    while day <= last:
        frame = frames.frame(day)
        if frame is not None:
            if frame.sunrise <= inst.start_jd < frame.next_sunrise:
                home = day
            if udaya is None and inst.start_jd <= frame.sunrise < inst.end_jd:
                udaya = day
            window = frames.window(frame, rule.kala)
            if window is not None:
                share = coverage(window, inst.start_jd, inst.end_jd, bhadra)
                if share > 0:
                    scored.append((day, share))
        day += timedelta(days=1)

    if not scored:
        return udaya or home
    if len(scored) == 1 or rule.tie is TieBreak.FIRST:
        return scored[0][0]
    if rule.tie is TieBreak.SECOND:
        return scored[1][0]
    return max(scored, key=lambda item: item[1])[0]  # first day wins an exact tie


def _render(template: str, months: LunarMonths, month_system: str) -> str:
    masa = months.purnimanta if month_system == "purnimanta" else months.amanta
    label = f"Adhika {masa.name}" if masa.is_adhika else masa.name
    return template.replace("{masa}", label)


def _tithi_span(inst: TithiInstance, frames: DayFrames) -> Span:
    index = inst.number - 1
    return Span(
        number=inst.number,
        id=names.tithi_id(index),
        name=names.TITHIS[index],
        start=from_jd(inst.start_jd, frames.tz),
        end=from_jd(inst.end_jd, frames.tz),
        paksha=names.paksha(index),
    )


def _lunar_occurrences(rule, instances, frames, profile) -> list[FestivalOccurrence]:
    result = []
    for inst in instances:
        if not _matches(rule, inst):
            continue
        day = _choose_day(rule, inst, frames, profile.ayanamsha)
        if day is None:
            continue  # no sunrise around this date at this location
        result.append(
            FestivalOccurrence(
                festival_id=rule.id,
                occurrence_id=f"{rule.id}:{from_jd(inst.start_jd, UTC).date()}",
                name=_render(rule.name, inst.months, profile.month_system),
                short_name=rule.short_name,
                category=rule.category,
                date=day,
                kala=rule.kala.value,
                tithi=_tithi_span(inst, frames),
                masa=inst.months,
            )
        )
    return result


def _solar_occurrences(rule: SolarRule, events: tuple[Sankranti, ...], frames: DayFrames,
                       claimed_signs: set[int]) -> list[FestivalOccurrence]:  # fmt: skip
    result = []
    for event in events:
        if rule.sign is not None and event.sign != rule.sign:
            continue
        if rule.sign is None and event.sign in claimed_signs:
            continue  # a sign-specific rule (e.g. Makar Sankranti) covers it
        day = frames.local_date(event.jd)
        frame = frames.frame(day)
        if frame is not None and event.jd >= frame.sunset:
            day += timedelta(days=1)  # after sunset: observed the next day
        result.append(
            FestivalOccurrence(
                festival_id=rule.id,
                occurrence_id=f"{rule.id}:{SIGN_IDS[event.sign]}:{from_jd(event.jd, UTC).year}",
                name=rule.name.replace("{sign}", SIGN_NAMES[event.sign]),
                short_name=rule.short_name,
                category=rule.category,
                date=day,
                kala=None,
                sankranti_time=from_jd(event.jd, frames.tz),
            )
        )
    return result


def festivals_for_year(
    year: int, location: Location, profile: CalculationProfile, festival_set: FestivalSet
) -> tuple[FestivalOccurrence, ...]:
    """All festival and observance occurrences whose local date falls in ``year``."""
    frames = DayFrames(location)
    instances = lunar_year(year, profile.ayanamsha)
    events = sankrantis(year, profile.ayanamsha)

    occurrences: list[FestivalOccurrence] = []
    for rule in festival_set.lunar:
        occurrences += _lunar_occurrences(rule, instances, frames, profile)
    claimed = {r.sign for r in festival_set.solar if r.sign is not None}
    for rule in festival_set.solar:
        occurrences += _solar_occurrences(rule, events, frames, claimed)

    in_year = [o for o in occurrences if o.date.year == year]
    # Major festivals first within a day, then by name, for a stable order.
    in_year.sort(key=lambda o: (o.date, o.category is not Category.MAJOR, o.name))
    return tuple(in_year)
