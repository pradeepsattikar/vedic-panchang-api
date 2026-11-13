"""Assign festivals and observances to local civil dates.

For a lunar rule, the festival falls on the civil day on which its Tithi prevails during
the rule's kala (e.g. Pradosh for Diwali); time under Bhadra does not count for rules that
avoid it. If the Tithi prevails in the kala on two days, the rule's tie-break decides. If
on neither, the day on which the Tithi prevails at sunrise is used (udaya tithi), and for a
Tithi that touches no sunrise, the Panchang day in which it begins.

Ekadashi (rules with a parana time): the fast must be broken within Dwadashi. When Ekadashi
begins after one sunrise and ends shortly after the next, and Dwadashi then ends before the
following sunrise, a fast on the udaya day could only be broken after Dwadashi. The Smarta
fast is then kept on the first day and broken on the udaya day; the udaya day is the
alternate (Gauna) Ekadashi. Drik Panchang, Prabodhini Ekadashi 2026, Kolkata: fast Nov 20,
parana Nov 21 12:28-2:40 PM (Gauna Nov 21).
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from vedic_panchang.astronomy.julian import from_jd
from vedic_panchang.domain.festivals import muhurta
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
class PujaTime:
    """A named puja / observance time; an instant (e.g. moonrise) has start == end."""

    id: str
    start: datetime
    end: datetime


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
    puja_times: tuple[PujaTime, ...] = ()
    sade_teen_muhurat: str | None = None  # "full" or "half" on the 3 1/2 auspicious days


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


def _ekadashi_day(
    day: date, inst: TithiInstance, dwadashi: TithiInstance | None, frames: DayFrames
) -> date:
    """Move an Ekadashi fast to the previous day when Dwadashi would end before the parana day."""
    frame, before, after = (
        frames.frame(day),
        frames.frame(day - timedelta(days=1)),
        frames.frame(day + timedelta(days=1)),
    )
    if dwadashi is None or frame is None or before is None or after is None:
        return day
    starts_after_previous_sunrise = before.sunrise < inst.start_jd < frame.sunrise
    if starts_after_previous_sunrise and dwadashi.end_jd <= after.sunrise:
        return day - timedelta(days=1)
    return day


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


def _puja_times(recipes, frames, ayanamsha, day, tithi=None, next_tithi=None, sankranti_jd=None):
    frame = frames.frame(day)
    if not recipes or frame is None:
        return ()
    ctx = muhurta.Context(frames, ayanamsha, day, frame, tithi, next_tithi, sankranti_jd)
    return tuple(
        PujaTime(w.id, from_jd(w.start, frames.tz), from_jd(w.end, frames.tz))
        for w in muhurta.puja_windows(recipes, ctx)
    )


def _lunar_occurrences(rule, instances, frames, profile) -> list[FestivalOccurrence]:
    result = []
    for position, inst in enumerate(instances):
        if not _matches(rule, inst):
            continue
        day = _choose_day(rule, inst, frames, profile.ayanamsha)
        if day is None:
            continue  # no sunrise around this date at this location
        following = instances[position + 1] if position + 1 < len(instances) else None
        if "parana" in rule.puja:
            day = _ekadashi_day(day, inst, following, frames)
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
                sade_teen_muhurat=rule.sade_teen_muhurat,
                puja_times=_puja_times(
                    rule.puja,
                    frames,
                    profile.ayanamsha,
                    day,
                    inst,
                    following,
                ),  # fmt: skip
            )
        )
    return result


def _solar_occurrences(rule: SolarRule, events: tuple[Sankranti, ...], frames: DayFrames,
                       claimed_signs: set[int], ayanamsha) -> list[FestivalOccurrence]:  # fmt: skip
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
                puja_times=_puja_times(rule.puja, frames, ayanamsha, day, sankranti_jd=event.jd),
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
        occurrences += _solar_occurrences(rule, events, frames, claimed, profile.ayanamsha)

    in_year = [o for o in occurrences if o.date.year == year]
    # Major festivals first within a day, then by name, for a stable order.
    in_year.sort(key=lambda o: (o.date, o.category is not Category.MAJOR, o.name))
    return tuple(in_year)
