"""Swiss Ephemeris adapter.

This is the only module in the code base that imports ``swisseph``. Everything above
this layer works with plain floats (Julian days in UT, longitudes in degrees), so the
engine can be upgraded or replaced without touching Panchang rules.

The Swiss Ephemeris C library keeps global state (e.g. the sidereal mode), so every call
is serialised with a lock. Individual calls take microseconds, so this is not a bottleneck.
"""

import threading
from dataclasses import dataclass
from enum import StrEnum

import swisseph as swe


class Body(StrEnum):
    SUN = "sun"
    MOON = "moon"
    MARS = "mars"
    MERCURY = "mercury"
    JUPITER = "jupiter"
    VENUS = "venus"
    SATURN = "saturn"
    MEAN_NODE = "mean_node"  # Rahu (mean lunar node); Ketu is opposite
    TRUE_NODE = "true_node"  # Rahu (true, osculating lunar node)


class Ayanamsha(StrEnum):
    LAHIRI = "lahiri"


class RiseSet(StrEnum):
    RISE = "rise"
    SET = "set"


_BODY_IDS = {
    Body.SUN: swe.SUN,
    Body.MOON: swe.MOON,
    Body.MARS: swe.MARS,
    Body.MERCURY: swe.MERCURY,
    Body.JUPITER: swe.JUPITER,
    Body.VENUS: swe.VENUS,
    Body.SATURN: swe.SATURN,
    Body.MEAN_NODE: swe.MEAN_NODE,
    Body.TRUE_NODE: swe.TRUE_NODE,
}
_SIDEREAL_MODES = {Ayanamsha.LAHIRI: swe.SIDM_LAHIRI}
_RISE_SET_FLAGS = {RiseSet.RISE: swe.CALC_RISE, RiseSet.SET: swe.CALC_SET}
# The Sun rises/sets at its upper limb with refraction (verified against Drik Panchang).
# Drik Panchang times the Moon at the centre of its disc, without refraction: with these flags
# moonrise/moonset match Drik within a minute (was 5-8 minutes; checked 2026-10-17 for London,
# Vancouver, Toronto, New York and Mumbai).
_BODY_RISE_SET_BITS = {
    Body.SUN: 0,
    Body.MOON: swe.BIT_DISC_CENTER | swe.BIT_NO_REFRACTION,
    # Planets (for Guru/Shukra asta): centre, no refraction; calibrated with the Moon's convention.
    Body.VENUS: swe.BIT_DISC_CENTER | swe.BIT_NO_REFRACTION,
    Body.JUPITER: swe.BIT_DISC_CENTER | swe.BIT_NO_REFRACTION,
}

# Built-in Moshier ephemeris: needs no data files and is the configuration that was
# verified against Drik Panchang (all elements within 1 minute).
_EPHEMERIS_FLAG = swe.FLG_MOSEPH

# Standard atmosphere used for refraction at rise/set (upper limb of the disc).
_PRESSURE_HPA = 1013.25
_TEMPERATURE_C = 15.0

_CIRCUMPOLAR = -2

_lock = threading.Lock()


@dataclass(frozen=True)
class EngineInfo:
    name: str
    library_version: str
    binding_version: str
    ephemeris: str


ENGINE_INFO = EngineInfo(
    name="Swiss Ephemeris",
    library_version=swe.version,
    binding_version=str(swe.__version__),
    ephemeris="moshier",
)


def sidereal_sun_moon(jd_ut: float, ayanamsha: Ayanamsha) -> tuple[float, float]:
    """Return the sidereal (sun, moon) ecliptic longitudes in degrees [0, 360)."""
    flags = _EPHEMERIS_FLAG | swe.FLG_SIDEREAL
    with _lock:
        swe.set_sid_mode(_SIDEREAL_MODES[ayanamsha], 0, 0)
        sun = swe.calc_ut(jd_ut, swe.SUN, flags)[0][0]
        moon = swe.calc_ut(jd_ut, swe.MOON, flags)[0][0]
    return sun, moon


def next_rise_or_set(
    jd_ut_start: float,
    body: Body,
    event: RiseSet,
    longitude: float,
    latitude: float,
    altitude_m: float,
) -> float | None:
    """Return the Julian day (UT) of the next rise/set after ``jd_ut_start``.

    Returns ``None`` when the body is circumpolar (does not rise or set), e.g. the Sun
    during polar night or midnight sun.
    """
    with _lock:
        result, times = swe.rise_trans(
            jd_ut_start,
            _BODY_IDS[body],
            _RISE_SET_FLAGS[event] | _BODY_RISE_SET_BITS[body],
            (longitude, latitude, altitude_m),
            _PRESSURE_HPA,
            _TEMPERATURE_C,
            _EPHEMERIS_FLAG,
        )
    if result == _CIRCUMPOLAR:
        return None
    return times[0]


def sidereal_ascendant(
    jd_ut: float, latitude: float, longitude: float, ayanamsha: Ayanamsha
) -> float:
    """Return the sidereal longitude of the ascendant (Lagna) in degrees [0, 360)."""
    with _lock:
        swe.set_sid_mode(_SIDEREAL_MODES[ayanamsha], 0, 0)
        _, ascmc = swe.houses_ex(jd_ut, latitude, longitude, b"W", swe.FLG_SIDEREAL)
    return ascmc[0] % 360.0


def geometric_rise_or_set(
    jd_ut_start: float,
    body: Body,
    event: RiseSet,
    longitude: float,
    latitude: float,
    altitude_m: float,
) -> float | None:
    """Rise/set of the body's centre without refraction (for kalamsha, where the Sun and the
    planet must be measured the same way). None when the body does not rise or set."""
    flags = _RISE_SET_FLAGS[event] | swe.BIT_DISC_CENTER | swe.BIT_NO_REFRACTION
    with _lock:
        result, times = swe.rise_trans(
            jd_ut_start, _BODY_IDS[body], flags, (longitude, latitude, altitude_m),
            _PRESSURE_HPA, _TEMPERATURE_C, _EPHEMERIS_FLAG,
        )  # fmt: skip
    return None if result == _CIRCUMPOLAR else times[0]


@dataclass(frozen=True)
class PlanetPosition:
    longitude: float  # tropical ecliptic longitude, degrees (only differences to the Sun are used)
    distance_au: float  # geocentric distance


def planet_position(jd_ut: float, body: Body) -> PlanetPosition:
    """Geocentric ecliptic longitude and distance of a body (for asta, i.e. combustion)."""
    with _lock:
        values = swe.calc_ut(jd_ut, _BODY_IDS[body], _EPHEMERIS_FLAG)[0]
    return PlanetPosition(longitude=values[0], distance_au=values[2])


def sidereal_longitude_and_speed(
    jd_ut: float, body: Body, ayanamsha: Ayanamsha
) -> tuple[float, float]:
    """Sidereal geocentric longitude (degrees [0, 360)) and its daily speed (negative while
    the body is retrograde)."""
    flags = _EPHEMERIS_FLAG | swe.FLG_SIDEREAL | swe.FLG_SPEED
    with _lock:
        swe.set_sid_mode(_SIDEREAL_MODES[ayanamsha], 0, 0)
        values = swe.calc_ut(jd_ut, _BODY_IDS[body], flags)[0]
    return values[0] % 360.0, values[3]
