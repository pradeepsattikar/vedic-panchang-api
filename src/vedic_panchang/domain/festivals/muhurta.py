"""Puja and observance times (muhurtas) for a festival occurrence.

Each muhurta is a named recipe built from the day frame (sunrise, sunset, next sunrise),
the festival's Tithi and, where the tradition needs them, Bhadra, the rising sign (Lagna)
and moonrise. The recipes follow Drik Panchang's published definitions; each one notes
the reference it was checked against (New Delhi unless stated).

A span is (start, end) in Julian days; an instant has start == end. A recipe returns None
when its time does not occur (e.g. the Tithi has ended), never a substitute time.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

from vedic_panchang.astronomy import ephemeris as eph
from vedic_panchang.domain.festivals.calendar import TithiInstance, bhadra_periods
from vedic_panchang.domain.festivals.kala import DayFrame, DayFrames

Span = tuple[float, float]

_MINUTE = 1.0 / 1440.0
_GHATI = 24 * _MINUTE
_LAGNA_STEP = 5 * _MINUTE
_LAGNA_PRECISION = 1.0 / 86400.0  # one second

# Sidereal signs by index (0 = Mesha).
VRISHABHA, KANYA = 1, 5


@dataclass(frozen=True)
class Context:
    frames: DayFrames
    ayanamsha: eph.Ayanamsha
    day: date  # local observance date
    frame: DayFrame
    tithi: TithiInstance | None  # lunar festivals
    next_tithi: TithiInstance | None  # the Tithi after it (Dwadashi for Ekadashi Parana)
    sankranti_jd: float | None = None  # solar festivals

    @property
    def daytime(self) -> float:
        return self.frame.sunset - self.frame.sunrise

    @property
    def night(self) -> float:
        return self.frame.next_sunrise - self.frame.sunset

    def day_part(self, start: float, end: float) -> Span:
        """Fractions of the daytime, e.g. (2/5, 3/5) for Madhyahna."""
        return self.frame.sunrise + start * self.daytime, self.frame.sunrise + end * self.daytime

    def night_part(self, start: float, end: float) -> Span:
        return self.frame.sunset + start * self.night, self.frame.sunset + end * self.night

    def in_tithi(self, span: Span | None) -> Span | None:
        if span is None or self.tithi is None:
            return span
        return _intersect(span, (self.tithi.start_jd, self.tithi.end_jd))


def _intersect(a: Span | None, b: Span | None) -> Span | None:
    if a is None or b is None:
        return None
    start, end = max(a[0], b[0]), min(a[1], b[1])
    return (start, end) if start < end else None


def lagna_spans(ctx: Context, sign: int, within: Span) -> list[Span]:
    """Periods inside ``within`` during which ``sign`` is rising at the location."""
    loc = ctx.frames.location

    def rising(jd: float) -> int:
        return int(eph.sidereal_ascendant(jd, loc.latitude, loc.longitude, ctx.ayanamsha) // 30)

    def boundary(lo: float, hi: float) -> float:
        inside = rising(lo) == sign
        while hi - lo > _LAGNA_PRECISION:
            mid = (lo + hi) / 2
            if (rising(mid) == sign) == inside:
                lo = mid
            else:
                hi = mid
        return hi

    spans: list[Span] = []
    start = within[0] if rising(within[0]) == sign else None
    jd = within[0]
    while jd < within[1]:
        nxt = min(jd + _LAGNA_STEP, within[1])
        before, after = rising(jd) == sign, rising(nxt) == sign
        if before != after:
            edge = boundary(jd, nxt)
            if after:
                start = edge
            else:
                spans.append((start, edge))
                start = None
        jd = nxt
    if start is not None:
        spans.append((start, within[1]))
    return spans


# ── Recipes ───────────────────────────────────────────────────────────────────────────


def _kala(
    start: float, end: float, night: bool = False, cut: bool = True
) -> Callable[[Context], Span | None]:
    """A part of the day or night; cut to the Tithi unless ``cut`` is False."""

    def recipe(ctx: Context) -> Span | None:
        part = ctx.night_part(start, end) if night else ctx.day_part(start, end)
        return ctx.in_tithi(part) if cut else part

    return recipe


def _muhurta(n: int) -> Callable[[Context], Span | None]:
    """The n-th (1-based) of the 15 daytime muhurtas, while the Tithi prevails."""
    return _kala((n - 1) / 15, n / 15)


def _prahar(n: int) -> Callable[[Context], Span | None]:
    """The n-th quarter of the night (Maha Shivaratri prahar puja); not cut to the Tithi."""
    return lambda ctx: ctx.night_part((n - 1) / 4, n / 4)


def _moonrise(ctx: Context) -> Span | None:
    jd = ctx.frames.moonrise(ctx.frame)
    return None if jd is None else (jd, jd)


def _pradosh_uncut(ctx: Context) -> Span | None:
    # Dev Deepawali (Varanasi 2025-11-05: 5:15-7:50 PM although Purnima ended at 6:48 PM).
    return ctx.night_part(0, 1 / 5)


def _sthir_lagna_pradosh(ctx: Context) -> Span | None:
    """Diwali Lakshmi Puja and Dhanteras: Pradosh while Vrishabha (a fixed sign) rises.

    Drik 2025-10-20: Pradosh 5:46-8:18 PM, Vrishabha 7:08-9:03 PM, Lakshmi Puja 7:08-8:18 PM.
    Drik 2024-11-01: no overlap with Vrishabha, so Pradosh while Amavasya prevails
    (5:36-6:16 PM).
    """
    pradosh = ctx.in_tithi(ctx.night_part(0, 1 / 5))
    if pradosh is None:
        return None
    for span in lagna_spans(ctx, VRISHABHA, pradosh):
        return span  # Vrishabha rises at most once in Pradosh
    return pradosh


def _ghatasthapana(lagna: int | None) -> Callable[[Context], Span | None]:
    """First third of the day while Pratipada prevails (Drik Chaitra 2025: 6:13-10:22 AM).

    Sharad Navratri also requires the dual sign Kanya rising (Drik 2025-09-22: 6:09-8:06 AM).
    """

    def recipe(ctx: Context) -> Span | None:
        span = ctx.in_tithi(ctx.day_part(0, 1 / 3))
        if span is None or lagna is None:
            return span
        spans = lagna_spans(ctx, lagna, span)
        return spans[0] if spans else None

    return recipe


def _sandhi(ctx: Context) -> Span | None:
    """Last 24 minutes of Ashtami and first 24 minutes of Navami."""
    if ctx.tithi is None:
        return None
    return ctx.tithi.end_jd - _GHATI, ctx.tithi.end_jd + _GHATI


def _bhadra(ctx: Context, span: Span) -> list[Span]:
    return bhadra_periods(ctx.ayanamsha, span[0] - 1.0, span[1] + 1.0)


def _rakhi(ctx: Context) -> Span | None:
    """Sunrise to the end of Pradosh, while Purnima prevails, outside Bhadra.

    Drik 2024-08-19: Bhadra ended 1:30 PM, Pradosh ended 9:08 PM -> 1:30-9:08 PM.
    """
    window = ctx.in_tithi((ctx.frame.sunrise, ctx.night_part(0, 1 / 5)[1]))
    if window is None:
        return None
    free = [window]
    for b_start, b_end in _bhadra(ctx, window):
        free = [piece for s, e in free for piece in ((s, min(e, b_start)), (max(s, b_end), e))]
        free = [(s, e) for s, e in free if s < e]
    return max(free, key=lambda s: s[1] - s[0]) if free else None


def _holika_dahan(ctx: Context) -> Span | None:
    """Pradosh while Purnima prevails, free of Bhadra. If Bhadra covers Pradosh but ends
    before midnight (the middle of the night), after Bhadra until midnight.

    Drik 2025-03-13: Bhadra to 11:26 PM -> 11:26 PM-12:30 AM; 2024-03-24: 11:13 PM-12:27 AM.
    Bhadra beyond midnight (Bhadra Punchha rule) is not modelled: no time is given.
    """
    pradosh = ctx.in_tithi(ctx.night_part(0, 1 / 5))
    if pradosh is None:
        return None
    overlapping = [b for b in _bhadra(ctx, pradosh) if _intersect(b, pradosh)]
    if not overlapping:
        return pradosh
    bhadra_end = max(e for _, e in overlapping)
    midnight = ctx.night_part(0, 1 / 2)[1]
    if bhadra_end < pradosh[1]:
        return ctx.in_tithi((bhadra_end, pradosh[1]))
    if bhadra_end < midnight:
        return ctx.in_tithi((bhadra_end, midnight))
    return None


def _abhyang_snan(ctx: Context) -> Span | None:
    """Moonrise to sunrise while Chaturdashi prevails (Drik 2025-10-20: 5:17-6:25 AM)."""
    sunrise = ctx.frame.sunrise
    moonrise = ctx.frames.next_moonrise(sunrise - 0.5)
    if moonrise is None or moonrise >= sunrise:
        return None
    return ctx.in_tithi((moonrise, sunrise))


def _upavasa(ctx: Context) -> Span | None:
    """Karwa Chauth fast: sunrise to moonrise (Drik 2026-10-29: 6:31 AM-8:17 PM)."""
    moonrise = ctx.frames.moonrise(ctx.frame)
    return None if moonrise is None else (ctx.frame.sunrise, moonrise)


def _sandhya_puja(ctx: Context) -> Span | None:
    """Karwa Chauth / Ahoi Ashtami evening puja: first tenth of the night.

    Drik Karwa Chauth 2026-10-29: 5:38-6:56 PM; Ahoi Ashtami 2025-10-13: 5:53-7:08 PM.
    """
    return ctx.night_part(0, 1 / 10)


def _star_sighting(ctx: Context) -> Span | None:
    """Ahoi Ashtami: stars are sighted one ghati after sunset (Drik 2025-10-13: 6:17 PM)."""
    jd = ctx.frame.sunset + _GHATI
    return jd, jd


def _sunset(ctx: Context) -> Span | None:
    return ctx.frame.sunset, ctx.frame.sunset


def _next_sunrise(ctx: Context) -> Span | None:
    return ctx.frame.next_sunrise, ctx.frame.next_sunrise


def _tithi_daytime(ctx: Context) -> Span | None:
    """Anant Chaturdashi: from sunrise while Chaturdashi prevails (Drik 2026: 6:11 AM-11:06 PM)."""
    return ctx.in_tithi((ctx.frame.sunrise, ctx.frame.next_sunrise))


def _parana(ctx: Context) -> Span | None:
    """Ekadashi fast-breaking on the next day, never during Hari Vasara (the first quarter
    of Dwadashi). In Pratahkala (first fifth of the day) and before Dwadashi ends;
    if Hari Vasara lasts beyond Pratahkala, in the afternoon (Aparahna) instead.

    Drik 2024-06-19 (Nirjala): 5:24-7:28 AM (Dwadashi ends 7:28 AM).
    Drik 2025-06-22 (Yogini): Hari Vasara to 9:41 AM -> 1:47-4:35 PM.
    """
    frame = ctx.frames.frame(ctx.day + timedelta(days=1))
    dwadashi = ctx.next_tithi
    if frame is None or dwadashi is None:
        return None
    hari_vasara_end = dwadashi.start_jd + (dwadashi.end_jd - dwadashi.start_jd) / 4
    daytime = frame.sunset - frame.sunrise
    pratah = (frame.sunrise, frame.sunrise + daytime / 5)
    aparahna = (frame.sunrise + 3 * daytime / 5, frame.sunrise + 4 * daytime / 5)
    window = pratah if hari_vasara_end < pratah[1] else aparahna
    start = max(window[0], hari_vasara_end)
    end = window[1]
    if dwadashi.end_jd > frame.sunrise:  # Parana should be done within Dwadashi
        end = min(end, dwadashi.end_jd)
    return (start, end) if start < end else None


def _punya_kaal(ctx: Context) -> Span | None:
    """Makar Sankranti: 40 ghatis from the Sun's ingress, in daylight.

    Drik 2025-01-14: ingress 9:03 AM -> 9:03 AM-5:46 PM.
    """
    if ctx.sankranti_jd is None:
        return None
    start = max(ctx.sankranti_jd, ctx.frame.sunrise)
    end = min(ctx.sankranti_jd + 40 * _GHATI, ctx.frame.sunset)
    return (start, end) if start < end else None


RECIPES: dict[str, Callable[[Context], Span | None]] = {
    "pratahkala": _kala(0, 1 / 5),  # Drik Hartalika Teej 2025-08-26: 5:56-8:31 AM
    # Not cut: Drik Vasant Panchami 2025-02-02 gives 7:09 AM-12:35 PM, Panchami from 9:14 AM.
    "purvahna": _kala(0, 1 / 2, cut=False),
    "madhyahna": _kala(2 / 5, 3 / 5),  # Drik Ganesh Chaturthi 2025-08-27: 11:05 AM-1:40 PM
    "aparahna": _kala(3 / 5, 4 / 5),  # Drik Dussehra 2025-10-02: 1:21-3:44 PM
    "sayankala": _kala(4 / 5, 1),  # Drik Govardhan Puja 2025-10-22: 3:29-5:44 PM
    "pradosh": _kala(0, 1 / 5, night=True),  # Drik Brampton 2026-10-23: 6:23-9:03 PM
    "nishita": _kala(7 / 15, 8 / 15, night=True),  # Drik Janmashtami 2025: 12:04-12:47 AM
    "kutup": _muhurta(8),  # Shraddha: Drik 2025-09-20: 11:50 AM-12:39 PM
    "rohina": _muhurta(9),
    "abhijit": _muhurta(8),  # Ghatasthapana alternative: Drik 2025-09-22: 11:49 AM-12:38 PM
    "vijay": _muhurta(11),  # Drik Dussehra 2025-10-02: 2:09-2:56 PM
    "prahar_1": _prahar(1),  # Drik Maha Shivaratri 2025-02-26: 6:19-9:26 PM
    "prahar_2": _prahar(2),
    "prahar_3": _prahar(3),
    "prahar_4": _prahar(4),
    "moonrise": _moonrise,
    "dev_deepawali": _pradosh_uncut,
    "lakshmi_puja": _sthir_lagna_pradosh,
    "dhanteras_puja": _sthir_lagna_pradosh,  # Drik 2025-10-18: 7:15-8:19 PM
    "ghatasthapana": _ghatasthapana(None),
    "ghatasthapana_kanya": _ghatasthapana(KANYA),
    "sandhi_puja": _sandhi,
    "rakhi": _rakhi,
    "holika_dahan": _holika_dahan,
    "abhyang_snan": _abhyang_snan,
    "upavasa": _upavasa,
    "sandhya_puja": _sandhya_puja,
    "star_sighting": _star_sighting,
    "sandhya_arghya": _sunset,  # Chhath: offering to the setting Sun
    "usha_arghya": _next_sunrise,  # Chhath: offering to the rising Sun, next morning
    "tithi_daytime": _tithi_daytime,
    "parana": _parana,
    "punya_kaal": _punya_kaal,
}

# Recipes that need the Tithi after the festival's Tithi.
NEEDS_NEXT_TITHI = frozenset({"parana"})


@dataclass(frozen=True)
class PujaWindow:
    id: str
    start: float
    end: float


def puja_windows(recipes: tuple[str, ...], ctx: Context) -> tuple[PujaWindow, ...]:
    result = []
    for name in recipes:
        span = RECIPES[name](ctx)
        if span is not None:
            result.append(PujaWindow(name, span[0], span[1]))
    return tuple(result)
