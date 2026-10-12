"""Daily Panchang for one location and local civil date.

Conventions (see rules/data/profiles.toml and the project decision log):
- The Panchang day runs from local sunrise to the next local sunrise (D04). Element
  values "at sunrise" are the day-anchor values; every span overlapping the Panchang day
  is also returned with its start and end instants.
- Rise/set searches are anchored at LOCAL midnight of the civil date, never UTC midnight.
- A rise/set that does not happen within the local civil day is reported as NO_EVENT
  (a valid outcome) together with the next occurrence, never as 00:00.
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
)
from vedic_panchang.domain.panchang.spans import RawSpan, spans_over
from vedic_panchang.domain.panchang.timings import day_timings
from vedic_panchang.rules.profiles import CalculationProfile

TITHI_DEG = 12.0
KARANA_DEG = 6.0
NAKSHATRA_DEG = 360.0 / 27.0
YOGA_DEG = 360.0 / 27.0

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

    def in_day(self, jd: float) -> bool:
        return self.day_start_jd <= jd < self.day_end_jd

    def celestial_event(
        self, body: eph.Body, event: eph.RiseSet, search_from: float
    ) -> tuple[CelestialEvent, float | None]:
        """Return the event for this civil day and its Julian day (None unless it occurs)."""
        jd = self.next_event(body, event, search_from)
        if jd is None:
            return (
                CelestialEvent(
                    EventStatus.UNAVAILABLE,
                    reason=f"The {body} does not {event} at this location around this date",
                ),
                None,
            )
        separation = self.moon_sun_separation(jd) if body is eph.Body.MOON else None
        if self.in_day(jd):
            return CelestialEvent(
                EventStatus.OCCURS, time=self.local(jd), moon_sun_separation_deg=separation
            ), jd
        return (
            CelestialEvent(
                EventStatus.NO_EVENT,
                next_time=self.local(jd),
                reason=f"No {body}{event} on this date",
                moon_sun_separation_deg=separation,
            ),
            None,
        )

    def moon_sun_separation(self, jd: float) -> float:
        elong = self.elongation(jd)
        return round(min(elong, 360.0 - elong), 2)

    # ── elements ─────────────────────────────────────────────
    def element(
        self, angle_fn, segment_deg: float, window: DayWindow, window_jd, make_span
    ) -> Element:
        raw = spans_over(angle_fn, segment_deg, *window_jd)
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

        sunrise, sunrise_jd = self.celestial_event(sun, rise, self.day_start_jd)
        # Sunset is searched from sunrise so it always belongs to the same daytime.
        sunset, sunset_jd = self.celestial_event(sun, set_, sunrise_jd or self.day_start_jd)
        moonrise, _ = self.celestial_event(moon, rise, self.day_start_jd)
        moonset, _ = self.celestial_event(moon, set_, self.day_start_jd)

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

        weekday = self.day.weekday()
        return DailyPanchang(
            date=self.day,
            vara=Vara(
                number=(weekday + 1) % 7 + 1,
                id=names.slug(names.VARAS[weekday]),
                name=names.VARAS[weekday],
            ),
            masa=lunar_months(self.elongation, self.sun_longitude, window_jd[0]),
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
        )


def calculate_daily_panchang(
    day: date, location: Location, profile: CalculationProfile
) -> DailyPanchang:
    return _Calculation(day, location, profile).run()
