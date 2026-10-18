"""Navagraha positions against Drik Panchang (planetary positions, sidereal, Lahiri)."""

from datetime import UTC, datetime

import pytest

from vedic_panchang.astronomy.ephemeris import Ayanamsha
from vedic_panchang.astronomy.julian import to_jd
from vedic_panchang.domain.panchang.grahas import graha_positions

# Drik Panchang, Toronto, 2026-10-18 07:00 EDT (11:00 UTC), mean Rahu/Ketu.
# (graha, rashi, degree, minute, second, nakshatra, pada, retrograde)
DRIK_TORONTO_2026_10_18 = [
    ("surya", "Tula", 0, 50, 59, "Chitra", 3, False),
    ("chandra", "Dhanu", 28, 29, 33, "Uttara Ashadha", 1, False),
    ("mangal", "Karka", 17, 17, 28, "Ashlesha", 1, False),
    ("budha", "Tula", 24, 47, 37, "Vishakha", 2, False),
    ("guru", "Karka", 28, 14, 25, "Ashlesha", 4, False),
    ("shukra", "Tula", 9, 51, 42, "Swati", 1, True),
    ("shani", "Meena", 15, 59, 10, "Uttara Bhadrapada", 4, True),
    ("rahu", "Kumbha", 2, 33, 0, "Dhanishtha", 3, True),
    ("ketu", "Simha", 2, 33, 0, "Magha", 1, True),
]


@pytest.fixture(scope="module")
def positions():
    at = datetime(2026, 10, 18, 11, 0, tzinfo=UTC)
    result = graha_positions(to_jd(at), at, Ayanamsha.LAHIRI, "mean")
    return {g.id: g for g in result.grahas}


@pytest.mark.parametrize("row", DRIK_TORONTO_2026_10_18, ids=lambda r: r[0])
def test_matches_drik(positions, row):
    gid, rashi, d, m, s, nakshatra, pada, retro = row
    g = positions[gid]
    assert (g.rashi, g.nakshatra, g.pada, g.retrograde) == (rashi, nakshatra, pada, retro)
    # Drik's Lahiri differs from Swiss Ephemeris's by a few arc-seconds (open item, D05):
    # all grahas agree within 40", well below the arc-minute the app shows.
    expected = d + m / 60 + s / 3600
    assert abs(g.degree_in_rashi - expected) * 3600 < 40


def test_ketu_opposite_rahu(positions):
    assert abs((positions["ketu"].longitude - positions["rahu"].longitude) % 360 - 180) < 1e-9


def test_daily_has_nine_grahas_at_sunrise(daily):
    body = daily("2026-10-18", city_id="6167865")
    grahas = body["grahas"]
    assert [g["id"] for g in grahas["grahas"]] == [
        "surya", "chandra", "mangal", "budha", "guru", "shukra", "shani", "rahu", "ketu",
    ]  # fmt: skip
    assert grahas["lunar_node"] == "mean"
    assert grahas["at"] == body["sun"]["sunrise"]["time"]
