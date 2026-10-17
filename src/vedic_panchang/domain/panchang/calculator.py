"""Daily Panchang for one location and local civil date.

Conventions (see rules/data/profiles.toml and the project decision log):
- The Panchang day runs from local sunrise to the next local sunrise (D04). Element
  values "at sunrise" are the day-anchor values; every span overlapping the Panchang day
  is also returned with its start and end instants.
- Sunrise/sunset belong to the local civil date; searches are anchored at LOCAL midnight,
  never UTC midnight.
- Moonrise/moonset belong to the Panchang day (sunrise to next sunrise), matching Drik
  Panchang (D06, confirmed 2026-10-12: Mumbai 2026-11-03 shows moonrise 02:08 on Nov 4).
  Without a sunrise (polar regions) the civil day is used instead.
- An event that does not happen within its window is reported as NO_EVENT (a valid
  outcome) together with the next occurrence, never as 00:00.
"""

from collections.abc import Callable
from datetime import date, datetime, time, timedelta

from vedic_panchang.astronomy import ephemeris as eph
from vedic_panchang.astronomy.julian import from_jd, to_jd
from vedic_panchang.domain.location import Location
from vedic_panchang.domain.panchang import names
from vedic_panchang.domain.panchang.masa import lunar_months
from vedic_panchang.domain.panchang.models import (
    CelestialEvent,
    DailyPanchang,
    DayWindow,
    DayWindowBasis,
    Element,
    EventStatus,
    Span,
    Vara,
    YearInfo,
)
from vedic_panchang.domain.panchang.spans import RawSpan, spans_over
from vedic_panchang.domain.panchang.timings import day_timings
from vedic_panchang.rules.profiles import CalculationProfile

TITHI_DEG = 12.0
KARANA_DEG = 6.0
NAKSHATRA_DEG = 360.0 / 27.0
YOGA_DEG = 360.0 / 27.0
RASHI_DEG = 30.0

_NO_SUNRISE = "The Sun does not rise on this date at this location"


class _Calculation:
    def __init__(self, day: date, location: Location, profile: CalculationProfile):
        self.day = day
        self.location = location
        self.profile = profile
        self.tz = location.tz
        self.day_start_jd = to_jd(datetime.combine(day, time(0), self.tz))
        self.day_end_jd = to_jd(datetime.combine(day + timedelta(days=1), time(0), self.tz))

    # ── helpers ──────────────────────────────────────────────
    def local(self, jd: float) -> datetime:
        return from_jd(jd, self.tz)

    def sun_moon(self, jd: float) -> tuple[float, float]:
        return eph.sidereal_sun_moon(jd, self.profile.ayanamsha)

    def elongation(self, jd: float) -> float:
        sun, moon = self.sun_moon(jd)
        return (moon - sun) % 360.0

    def sun_longitude(self, jd: float) -> float:
        return self.sun_moon(jd)[0]

    def moon_longitude(self, jd: float) -> float:
        return self.sun_moon(jd)[1]

    def sun_plus_moon(self, jd: float) -> float:
        sun, moon = self.sun_moon(jd)
        return (sun + moon) % 360.0

    def next_event(self, body: eph.Body, event: eph.RiseSet, search_from: float) -> float | None:
        loc = self.location
        return eph.next_rise_or_set(
            search_from, body, event, loc.longitude, loc.latitude, loc.altitude_m
        )

    def celestial_event(
        self,
        body: eph.Body,
        event: eph.RiseSet,
        window: tuple[float, float],
        search_from: float | None = None,
        window_name: str = "on this date",
    ) -> tuple[CelestialEvent, float | None]:
        """Return the event within ``window`` and its Julian day (None unless it occurs)."""
        start, end = window
        jd = self.next_event(body, event, start if search_from is None else search_from)
        if jd is None:
            return (
                CelestialEvent(
                    EventStatus.UNAVAILABLE,
                    reason=f"The {body} does not {event} at this location around this date",
                ),
                None,
            )
        separation = self.moon_sun_separation(jd) if body is eph.Body.MOON else None
        if start <= jd < end:
            return CelestialEvent(
                EventStatus.OCCURS, time=self.local(jd), moon_sun_separation_deg=separation
            ), jd
        return (
            CelestialEvent(
                EventStatus.NO_EVENT,
                next_time=self.local(jd),
                reason=f"No {body}{event} {window_name}",
                moon_sun_separation_deg=separation,
            ),
            None,
        )

    def moon_sun_separation(self, jd: float) -> float:
        elong = self.elongation(jd)
        return round(min(elong, 360.0 - elong), 2)

    # ── elements ─────────────────────────────────────────────
    def element(
        self, angle_fn, segment_deg: float, window: DayWindow, window_jd, make_span, search_days=2.0
    ) -> Element:
        raw = spans_over(angle_fn, segment_deg, *window_jd, search_days=search_days)
        spans = tuple(make_span(r) for r in raw)
        if window.basis is DayWindowBasis.SUNRISE_TO_NEXT_SUNRISE:
            return Element(at_sunrise=spans[0], spans=spans)
        return Element(at_sunrise=None, spans=spans, unavailable_reason=_NO_SUNRISE)

    def tithi_span(self, r: RawSpan) -> Span:
        return Span(
            number=r.index + 1,
            id=names.tithi_id(r.index),
            name=names.TITHIS[r.index],
            start=self.local(r.start_jd),
            end=self.local(r.end_jd),
            paksha=names.paksha(r.index),
        )

    def named_span(self, table) -> Callable[[RawSpan], Span]:
        def make(r: RawSpan) -> Span:
            name = table[r.index]
            return Span(r.index + 1, names.slug(name), name, self.local(r.start_jd),
                        self.local(r.end_jd))  # fmt: skip

        return make

    def karana_span(self, r: RawSpan) -> Span:
        name = names.karana_name(r.index)
        return Span(r.index + 1, names.slug(name), name, self.local(r.start_jd),
                    self.local(r.end_jd))  # fmt: skip

    # ── main ─────────────────────────────────────────────────
    def run(self) -> DailyPanchang:
        sun, moon = eph.Body.SUN, eph.Body.MOON
        rise, set_ = eph.RiseSet.RISE, eph.RiseSet.SET

        civil_day = (self.day_start_jd, self.day_end_jd)
        sunrise, sunrise_jd = self.celestial_event(sun, rise, civil_day)
        # Sunset is searched from sunrise so it always belongs to the same daytime.
        sunset, sunset_jd = self.celestial_event(sun, set_, civil_day, search_from=sunrise_jd)

        next_sunrise_jd = None
        if sunrise_jd is not None and sunset_jd is not None:
            next_sunrise_jd = self.next_event(sun, rise, sunset_jd)

        if next_sunrise_jd is not None and next_sunrise_jd - sunrise_jd < 1.5:
            basis = DayWindowBasis.SUNRISE_TO_NEXT_SUNRISE
            window_jd = (sunrise_jd, next_sunrise_jd)
        else:
            basis = DayWindowBasis.CIVIL_DAY
            window_jd = (self.day_start_jd, self.day_end_jd)
        window = DayWindow(basis, self.local(window_jd[0]), self.local(window_jd[1]))

        moon_window_name = (
            "between sunrise and the next sunrise"
            if basis is DayWindowBasis.SUNRISE_TO_NEXT_SUNRISE
            else "on this date"
        )
        moonrise, _ = self.celestial_event(moon, rise, window_jd, window_name=moon_window_name)
        moonset, _ = self.celestial_event(moon, set_, window_jd, window_name=moon_window_name)

        weekday = self.day.weekday()
        masa = lunar_months(self.elongation, self.sun_longitude, window_jd[0])
        return DailyPanchang(
            date=self.day,
            vara=Vara(
                number=(weekday + 1) % 7 + 1,
                id=names.slug(names.VARAS[weekday]),
                name=names.VARAS[weekday],
            ),
            masa=masa,
            day_window=window,
            sunrise=sunrise,
            sunset=sunset,
            moonrise=moonrise,
            moonset=moonset,
            tithi=self.element(self.elongation, TITHI_DEG, window, window_jd, self.tithi_span),
            nakshatra=self.element(
                self.moon_longitude,
                NAKSHATRA_DEG,
                window,
                window_jd,
                self.named_span(names.NAKSHATRAS),
            ),  # fmt: skip
            yoga=self.element(
                self.sun_plus_moon, YOGA_DEG, window, window_jd, self.named_span(names.YOGAS)
            ),
            karana=self.element(self.elongation, KARANA_DEG, window, window_jd, self.karana_span),
            timings=day_timings(sunrise_jd, sunset_jd, weekday, self.profile, self.local),
            # The Sun stays ~30 days in a Rashi, the Moon ~2.5 days.
            sun_sign=self.element(
                self.sun_longitude,
                RASHI_DEG,
                window,
                window_jd,
                self.named_span(names.RASHIS),
                search_days=33.0,
            ),
            moon_sign=self.element(
                self.moon_longitude,
                RASHI_DEG,
                window,
                window_jd,
                self.named_span(names.RASHIS),
                search_days=3.0,
            ),  # fmt: skip
            year=self.year_info(masa.amanta.number, self.sun_longitude(window_jd[0])),
        )

    def year_info(self, amanta_month: int, sun_longitude: float) -> YearInfo:
        """The Samvat year turns at Chaitra Shukla Pratipada (the start of Amanta Chaitra):
        January to April dates still in Pausha, Magha or Phalguna belong to the old year."""
        old_year = self.day.month <= 4 and amanta_month >= 10
        vikram = self.day.year + (56 if old_year else 57)
        uttarayana = int(sun_longitude // 30) in (9, 10, 11, 0, 1, 2)
        return YearInfo(
            vikram_samvat=vikram,
            shaka_samvat=vikram - 135,
            ritu=names.RITUS[(amanta_month - 1) // 2],
            ayana="Uttarayana" if uttarayana else "Dakshinayana",
        )


def calculate_daily_panchang(
    day: date, location: Location, profile: CalculationProfile
) -> DailyPanchang:
    return _Calculation(day, location, profile).run()
