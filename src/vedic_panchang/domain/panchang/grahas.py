"""Positions of the nine grahas (Navagraha) at one instant: facts only, no interpretation.

Sidereal (Lahiri) geocentric longitudes from Swiss Ephemeris. Rahu is the lunar node (mean or
true, by profile); Ketu is exactly opposite. A graha is vakri (retrograde) while its longitude
decreases; the mean Rahu and Ketu always move backwards, as Drik Panchang shows.
"""

from dataclasses import dataclass
from datetime import datetime

from vedic_panchang.astronomy import ephemeris as eph
from vedic_panchang.domain.panchang import names

NAKSHATRA_DEG = 360.0 / 27.0
PADA_DEG = NAKSHATRA_DEG / 4.0

# (id, Sanskrit name, English name, body); Ketu is derived from Rahu.
GRAHAS = (
    ("surya", "Surya", "Sun", eph.Body.SUN),
    ("chandra", "Chandra", "Moon", eph.Body.MOON),
    ("mangal", "Mangal", "Mars", eph.Body.MARS),
    ("budha", "Budha", "Mercury", eph.Body.MERCURY),
    ("guru", "Guru", "Jupiter", eph.Body.JUPITER),
    ("shukra", "Shukra", "Venus", eph.Body.VENUS),
    ("shani", "Shani", "Saturn", eph.Body.SATURN),
)
_NODES = {"mean": eph.Body.MEAN_NODE, "true": eph.Body.TRUE_NODE}


@dataclass(frozen=True)
class GrahaPosition:
    id: str
    name: str  # Sanskrit
    english: str
    longitude: float  # sidereal, degrees [0, 360)
    rashi_number: int  # 1 = Mesha ... 12 = Meena
    rashi: str
    degree_in_rashi: float  # degrees [0, 30)
    nakshatra_number: int  # 1 = Ashwini ... 27 = Revati
    nakshatra: str
    pada: int  # 1-4
    retrograde: bool


@dataclass(frozen=True)
class GrahaPositions:
    at: datetime  # the instant (sunrise of the Panchang day, or the start of the civil day)
    lunar_node: str  # "mean" or "true"
    grahas: tuple[GrahaPosition, ...]


def _position(gid: str, name: str, english: str, lon: float, speed: float) -> GrahaPosition:
    lon %= 360.0
    rashi = int(lon // 30.0)
    nak = int(lon // NAKSHATRA_DEG)
    return GrahaPosition(
        id=gid,
        name=name,
        english=english,
        longitude=lon,
        rashi_number=rashi + 1,
        rashi=names.RASHIS[rashi],
        degree_in_rashi=lon - rashi * 30.0,
        nakshatra_number=nak + 1,
        nakshatra=names.NAKSHATRAS[nak],
        pada=int((lon % NAKSHATRA_DEG) // PADA_DEG) + 1,
        retrograde=speed < 0,
    )


def graha_positions(
    jd_ut: float, at: datetime, ayanamsha: eph.Ayanamsha, lunar_node: str
) -> GrahaPositions:
    out = []
    for gid, name, english, body in GRAHAS:
        lon, speed = eph.sidereal_longitude_and_speed(jd_ut, body, ayanamsha)
        out.append(_position(gid, name, english, lon, speed))
    rahu, speed = eph.sidereal_longitude_and_speed(jd_ut, _NODES[lunar_node], ayanamsha)
    out.append(_position("rahu", "Rahu", "North node", rahu, speed))
    out.append(_position("ketu", "Ketu", "South node", rahu + 180.0, speed))
    return GrahaPositions(at=at, lunar_node=lunar_node, grahas=tuple(out))
