"""Gochara: the nine grahas' transits counted from each natal Moon sign, over a week.

Facts and rule ids only, no prediction text. Planet signs are the same everywhere on Earth at
a given instant, so one result serves every city; the timezone only sets where the week starts
and ends and how the times are shown.

Steps (each testable on its own):
1. Sign spans of all nine grahas over the window (exact sign-change instants), retrograde
   stations and combustion spans.
2. For each of the 12 Moon signs, each graha's house counted from that sign (whole signs).
3. The rule set's favourable houses; a favourable result is obstructed (Vedha) while another
   graha occupies its Vedha house, except for exempt pairs.
4. Saturn's standing periods (Sade Sati, Dhaiya).
5. Highlights in the rule set's fixed order.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from vedic_panchang.astronomy import ephemeris as eph
from vedic_panchang.astronomy.julian import from_jd, to_jd
from vedic_panchang.domain.panchang import names
from vedic_panchang.rules.gochar import GRAHA_IDS, GocharRules

_BODIES = {
    "surya": eph.Body.SUN,
    "chandra": eph.Body.MOON,
    "mangal": eph.Body.MARS,
    "budha": eph.Body.MERCURY,
    "guru": eph.Body.JUPITER,
    "shukra": eph.Body.VENUS,
    "shani": eph.Body.SATURN,
}
_NODES = {"mean": eph.Body.MEAN_NODE, "true": eph.Body.TRUE_NODE}
# Sampling steps (days): short enough that no graha can leave and re-enter a sign, or turn
# twice, between two samples. The Moon moves ~13 deg/day; the others under 2.5 deg/day.
_STEP_DAYS = {"chandra": 0.125}
_DEFAULT_STEP = 0.5
_BISECTION_STEPS = 40  # 7 days / 2**40: far below a second
_STATION_GRAHAS = ("mangal", "budha", "guru", "shukra", "shani")  # Sun/Moon never; nodes: mean
# node always retrograde (true node wobbles daily, so its "stations" are not reported)
SLOW = ("guru", "shani", "rahu", "ketu")
FAST = ("surya", "budha", "shukra", "mangal")


def house_from_moon(transit_sign: int, moon_sign: int) -> int:
    """Whole-sign house (1-12) of a graha in ``transit_sign`` counted from ``moon_sign``
    (both 0 = Mesha ... 11 = Meena)."""
    return (transit_sign - moon_sign) % 12 + 1


# ── step 1: positions over the window ───────────────────────────


@dataclass(frozen=True)
class SignSpan:
    graha: str
    sign: int  # 0 = Mesha ... 11 = Meena
    start_jd: float  # clipped to the window
    end_jd: float
    entered_in_window: bool  # the graha entered this sign during the window


@dataclass(frozen=True)
class Station:
    graha: str
    jd: float
    becomes: str  # "retrograde" | "direct"


@dataclass(frozen=True)
class CombustSpan:
    graha: str
    start_jd: float
    end_jd: float


@dataclass(frozen=True)
class GrahaAtStart:
    graha: str
    longitude: float
    retrograde: bool


class _Sky:
    """Sidereal longitude and speed of each graha (Ketu = Rahu + 180)."""

    def __init__(self, ayanamsha: eph.Ayanamsha, lunar_node: str):
        self.ayanamsha = ayanamsha
        self.node = _NODES[lunar_node]

    def lon_speed(self, graha: str, jd: float) -> tuple[float, float]:
        if graha in ("rahu", "ketu"):
            lon, speed = eph.sidereal_longitude_and_speed(jd, self.node, self.ayanamsha)
            return (lon + (180.0 if graha == "ketu" else 0.0)) % 360.0, speed
        return eph.sidereal_longitude_and_speed(jd, _BODIES[graha], self.ayanamsha)

    def sign(self, graha: str, jd: float) -> int:
        return int(self.lon_speed(graha, jd)[0] // 30.0) % 12


def _bisect(changed: Callable[[float], bool], lo: float, hi: float) -> float:
    """Instant in (lo, hi] where ``changed`` turns True (False at lo, True at hi)."""
    for _ in range(_BISECTION_STEPS):
        mid = (lo + hi) / 2.0
        if changed(mid):
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2.0


def _samples(start: float, end: float, step: float) -> list[float]:
    count = max(1, int((end - start) / step + 0.999999))
    return [start + (end - start) * i / count for i in range(count + 1)]


def _changes(value: Callable[[float], object], start: float, end: float, step: float):
    """(instant, new value) for each change of ``value`` over [start, end]."""
    out = []
    times = _samples(start, end, step)
    previous = value(times[0])
    for lo, hi in zip(times, times[1:], strict=False):
        current = value(hi)
        if current != previous:
            before = previous
            out.append((_bisect(lambda t, b=before: value(t) != b, lo, hi), current))
            previous = current
    return out


def sign_spans(sky: _Sky, graha: str, start: float, end: float) -> tuple[SignSpan, ...]:
    step = _STEP_DAYS.get(graha, _DEFAULT_STEP)
    spans = []
    sign, since, entered = sky.sign(graha, start), start, False
    for jd, new_sign in _changes(lambda t: sky.sign(graha, t), start, end, step):
        spans.append(SignSpan(graha, sign, since, jd, entered))
        sign, since, entered = new_sign, jd, True
    spans.append(SignSpan(graha, sign, since, end, entered))
    return tuple(spans)


def stations(sky: _Sky, graha: str, start: float, end: float) -> tuple[Station, ...]:
    retro = lambda t: sky.lon_speed(graha, t)[1] < 0  # noqa: E731
    return tuple(Station(graha, jd, "retrograde" if now else "direct")
                 for jd, now in _changes(retro, start, end, _DEFAULT_STEP))  # fmt: skip


def _separation(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def combust_spans(
    sky: _Sky, rules: GocharRules, graha: str, start: float, end: float
) -> tuple[CombustSpan, ...]:
    if graha not in rules.combustion:
        return ()

    def combust(t: float) -> bool:
        lon, speed = sky.lon_speed(graha, t)
        orb = rules.combustion[graha]
        if speed < 0:
            orb = rules.combustion.get(f"{graha}_retrograde", orb)
        return _separation(lon, sky.lon_speed("surya", t)[0]) < orb

    step = _STEP_DAYS.get(graha, _DEFAULT_STEP)
    spans, since = [], start if combust(start) else None
    for jd, now in _changes(combust, start, end, step):
        if now:
            since = jd
        elif since is not None:
            spans.append(CombustSpan(graha, since, jd))
            since = None
    if since is not None:
        spans.append(CombustSpan(graha, since, end))
    return tuple(spans)


# ── steps 2-4: judgment per Moon sign ───────────────────────────


@dataclass(frozen=True)
class Judgment:
    house: int
    status: str  # "favourable" | "obstructed" | "unfavourable"
    vedha_house: int | None  # for favourable houses
    vedha_by: tuple[str, ...]  # grahas in the Vedha house (obstructed only)


def judge(rules: GocharRules, graha: str, signs: dict[str, int], moon_sign: int) -> Judgment:
    """Step 2-3 for one graha at one instant: ``signs`` holds every graha's sign (0-11)."""
    house = house_from_moon(signs[graha], moon_sign)
    vedha_house = rules.favourable[graha].get(house)
    if vedha_house is None:
        return Judgment(house, "unfavourable", None, ())
    by = tuple(
        other
        for other in GRAHA_IDS
        if other != graha
        and house_from_moon(signs[other], moon_sign) == vedha_house
        and rules.causes_vedha(other)
        and not rules.is_exempt(graha, other)
    )
    return Judgment(house, "obstructed" if by else "favourable", vedha_house, by)


def rule_id(graha: str, j: Judgment) -> str:
    """Stable id of the interpretation rule behind a judgment (the client's text key)."""
    base = f"{graha}_h{j.house}"
    return f"{base}_vedha" if j.status == "obstructed" else base


@dataclass(frozen=True)
class TransitPeriod:
    graha: str
    sign: int
    house: int
    status: str
    vedha_house: int | None
    vedha_by: tuple[str, ...]
    rule_id: str
    start_jd: float
    end_jd: float
    entered_in_window: bool


@dataclass(frozen=True)
class ShaniFlag:
    id: str
    name: str
    start_jd: float
    end_jd: float


@dataclass(frozen=True)
class Highlight:
    kind: str  # one of rules.highlight_order
    graha: str | None
    rule_ids: tuple[str, ...]
    jd: float | None  # instant of an ingress or station
    detail: str | None  # station direction, Shani period id


@dataclass(frozen=True)
class MoonSignWeek:
    moon_sign: int
    shani_flags: tuple[ShaniFlag, ...]
    transits: tuple[TransitPeriod, ...]  # graha order, then time order
    highlights: tuple[Highlight, ...]


@dataclass(frozen=True)
class GocharWeek:
    start: datetime
    end: datetime
    rules: GocharRules
    lunar_node: str
    at_start: tuple[GrahaAtStart, ...]
    sign_spans: dict[str, tuple[SignSpan, ...]]
    stations: tuple[Station, ...]
    combust: tuple[CombustSpan, ...]
    moon_signs: tuple[MoonSignWeek, ...]

    def at(self, jd: float) -> datetime:
        """A Julian day as a local time in the window's timezone."""
        return from_jd(jd, self.start.tzinfo)

    @staticmethod
    def rashi(sign: int) -> str:
        return names.RASHIS[sign]


def _intervals(spans: dict[str, tuple[SignSpan, ...]], start: float, end: float):
    """Split the window wherever any graha changes sign: (start, end, {graha: sign})."""
    cuts = sorted({start, end, *(s.start_jd for ss in spans.values() for s in ss)})
    out = []
    for a, b in zip(cuts, cuts[1:], strict=False):
        mid = (a + b) / 2.0
        signs = {g: next(s.sign for s in ss if s.start_jd <= mid < s.end_jd)
                 for g, ss in spans.items()}  # fmt: skip
        out.append((a, b, signs))
    return out


def _transits(rules, spans, intervals, moon_sign) -> tuple[TransitPeriod, ...]:
    out = []
    for graha in GRAHA_IDS:
        periods: list[TransitPeriod] = []
        for a, b, signs in intervals:
            j = judge(rules, graha, signs, moon_sign)
            key = (signs[graha], j.status, j.vedha_by)
            last = periods[-1] if periods else None
            if last and (last.sign, last.status, last.vedha_by) == key:
                periods[-1] = TransitPeriod(**{**last.__dict__, "end_jd": b})
                continue
            span = next(s for s in spans[graha] if s.start_jd <= a < s.end_jd)
            entered = span.entered_in_window and span.start_jd == a
            periods.append(TransitPeriod(graha, signs[graha], j.house, j.status, j.vedha_house,
                                         j.vedha_by, rule_id(graha, j), a, b, entered))  # fmt: skip
        out.extend(periods)
    return tuple(out)


def _shani_flags(rules, spans, moon_sign) -> tuple[ShaniFlag, ...]:
    flags = []
    for span in spans["shani"]:
        house = house_from_moon(span.sign, moon_sign)
        for period in rules.shani_periods:
            if period.house == house:
                flags.append(ShaniFlag(period.id, period.name, span.start_jd, span.end_jd))
    return tuple(flags)


def _highlights(rules, transits, shani_flags, all_stations) -> tuple[Highlight, ...]:
    by_graha: dict[str, list[TransitPeriod]] = {}
    for t in transits:
        by_graha.setdefault(t.graha, []).append(t)
    moved = {
        g for g, ps in by_graha.items() if g != "chandra" and any(p.entered_in_window for p in ps)
    }
    groups: dict[str, list[Highlight]] = {k: [] for k in rules.highlight_order}
    for flag in shani_flags:
        groups["shani_period"].append(Highlight("shani_period", "shani", (flag.id,), None, flag.id))
    for graha in GRAHA_IDS:
        if graha in moved:
            for p in by_graha[graha]:
                if p.entered_in_window:
                    groups["ingress"].append(
                        Highlight("ingress", graha, (p.rule_id,), p.start_jd, None)
                    )
    for s in all_stations:
        current = next(p for p in by_graha[s.graha] if p.start_jd <= s.jd <= p.end_jd)
        groups["station"].append(Highlight("station", s.graha, (current.rule_id,), s.jd, s.becomes))
    for kind, members in (("slow", SLOW), ("fast", FAST)):
        for graha in members:
            if graha not in moved:
                ids = tuple(dict.fromkeys(p.rule_id for p in by_graha[graha]))
                groups[kind].append(Highlight(kind, graha, ids, None, None))
    moon_ids = tuple(p.rule_id for p in by_graha["chandra"])
    groups["moon"].append(Highlight("moon", "chandra", moon_ids, None, None))
    return tuple(h for kind in rules.highlight_order for h in groups[kind])


def weekly_gochar(
    start: date,
    days: int,
    tz: ZoneInfo,
    ayanamsha: eph.Ayanamsha,
    lunar_node: str,
    rules: GocharRules,
) -> GocharWeek:
    """Gochara for every Moon sign from local midnight of ``start`` for ``days`` days."""
    begin = datetime.combine(start, time(0), tz)
    finish = datetime.combine(start + timedelta(days=days), time(0), tz)
    jd0, jd1 = to_jd(begin), to_jd(finish)
    sky = _Sky(ayanamsha, lunar_node)

    spans = {g: sign_spans(sky, g, jd0, jd1) for g in GRAHA_IDS}
    all_stations = tuple(s for g in _STATION_GRAHAS for s in stations(sky, g, jd0, jd1))
    combust = tuple(c for g in GRAHA_IDS for c in combust_spans(sky, rules, g, jd0, jd1))
    at_start = []
    for g in GRAHA_IDS:
        lon, speed = sky.lon_speed(g, jd0)
        at_start.append(GrahaAtStart(g, lon, speed < 0))
    intervals = _intervals(spans, jd0, jd1)

    weeks = []
    for moon_sign in range(12):
        transits = _transits(rules, spans, intervals, moon_sign)
        flags = _shani_flags(rules, spans, moon_sign)
        weeks.append(MoonSignWeek(moon_sign, flags, transits,
                                  _highlights(rules, transits, flags, all_stations)))  # fmt: skip
    return GocharWeek(begin, finish, rules, lunar_node, tuple(at_start), spans, all_stations,
                      combust, tuple(weeks))  # fmt: skip
