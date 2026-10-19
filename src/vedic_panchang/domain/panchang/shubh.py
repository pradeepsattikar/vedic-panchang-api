"""Shubh Yogas within a Panchang day: when an auspicious weekday/Nakshatra/Tithi combination
holds. Facts only.

The weekday is the Vara of the Panchang day (sunrise to next sunrise). The day is cut at every
Tithi, Nakshatra (Moon's and Sun's) change; each piece is judged at its midpoint and consecutive
matching pieces are joined into one window.
"""

from dataclasses import dataclass
from datetime import datetime

from vedic_panchang.domain.panchang.models import Element
from vedic_panchang.rules.shubh import ShubhRules, ShubhYogaRule


@dataclass(frozen=True)
class ShubhYoga:
    id: str
    name: str
    how: str
    note: str | None
    special: bool
    start: datetime
    end: datetime


def _at(element: Element, moment: datetime):
    for span in element.spans:
        if span.start <= moment < span.end:
            return span
    return None


def shubh_yogas(
    rules: ShubhRules,
    weekday: int,
    day_start: datetime,
    day_end: datetime,
    tithi: Element,
    nakshatra: Element,
    sun_nakshatra: Element,
) -> tuple[ShubhYoga, ...]:
    """Windows of each Shubh Yoga within [day_start, day_end) (the Panchang day)."""
    cuts = {day_start, day_end}
    for element in (tithi, nakshatra, sun_nakshatra):
        for span in element.spans:
            cuts.update(t for t in (span.start, span.end) if day_start < t < day_end)
    edges = sorted(cuts)
    pieces = []
    for a, b in zip(edges, edges[1:], strict=False):
        mid = a + (b - a) / 2
        t, n, s = _at(tithi, mid), _at(nakshatra, mid), _at(sun_nakshatra, mid)
        if t and n and s:
            pieces.append((a, b, t.number, n.id, n.number - 1, s.number - 1))
    out = []
    for rule in rules.yogas:
        out.extend(_windows(rule, weekday, pieces))
    return tuple(sorted(out, key=lambda y: (y.start, y.name)))


def _windows(rule: ShubhYogaRule, weekday: int, pieces) -> list[ShubhYoga]:
    windows: list[ShubhYoga] = []
    start = end = None
    for a, b, tithi, nak_id, moon_nak, sun_nak in pieces:
        if rule.matches(weekday, nak_id, tithi, sun_nak, moon_nak):
            start = a if start is None or end != a else start
            end = b
            continue
        if start is not None:
            windows.append(_yoga(rule, start, end))
            start = end = None
    if start is not None:
        windows.append(_yoga(rule, start, end))
    return windows


def _yoga(rule: ShubhYogaRule, start: datetime, end: datetime) -> ShubhYoga:
    return ShubhYoga(rule.id, rule.name, rule.how, rule.note, rule.special, start, end)
