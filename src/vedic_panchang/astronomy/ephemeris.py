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


class Ayanamsha(StrEnum):
    LAHIRI = "lahiri"


class RiseSet(StrEnum):
    RISE = "rise"
    SET = "set"


_BODY_IDS = {Body.SUN: swe.SUN, Body.MOON: swe.MOON}
_SIDEREAL_MODES = {Ayanamsha.LAHIRI: swe.SIDM_LAHIRI}
_RISE_SET_FLAGS = {RiseSet.RISE: swe.CALC_RISE, RiseSet.SET: swe.CALC_SET}

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
            _RISE_SET_FLAGS[event],
            (longitude, latitude, altitude_m),
            _PRESSURE_HPA,
            _TEMPERATURE_C,
            _EPHEMERIS_FLAG,
        )
    if result == _CIRCUMPOLAR:
        return None
    return times[0]
