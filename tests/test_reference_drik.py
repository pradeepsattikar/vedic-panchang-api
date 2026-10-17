"""Reference comparison against Drik Panchang (EN-19, D10 tolerances).

Values were read manually from drikpanchang.com on 2026-10-10 for the same GeoNames city
IDs (see notes/discussion_2026-10-10_engine_verification.md in the planning repository).
Tolerance: timings within 1 minute; names exact. Moonrise/moonset within 2 minutes
(Drik times the Moon at the centre of its disc without refraction; we do the same).

To add a reference case: read the values from Drik Panchang for a city ID in our
catalogue and add an entry below. Do not scrape the site.
"""

import pytest

from tests.conftest import minutes_apart

DATE = "2026-10-10"

REFERENCE = {
    "toronto": {
        "city_id": "6167865",
        "sunrise": "2026-10-10T07:26", "sunset": "2026-10-10T18:43",
        "moonrise": "2026-10-10T07:32", "moonset": "2026-10-10T18:19",
        "tithi_end": "2026-10-10T11:49", "nakshatra_end": "2026-10-10T12:12",
        "rahu_kalam": ("2026-10-10T10:15", "2026-10-10T11:40"),
        "yamaganda": ("2026-10-10T14:29", "2026-10-10T15:53"),
        "gulika_kalam": ("2026-10-10T07:26", "2026-10-10T08:51"),
        "abhijit_muhurta": ("2026-10-10T12:42", "2026-10-10T13:27"),
        "brahma_muhurta": ("2026-10-10T05:44", "2026-10-10T06:35"),
    },
    "vancouver": {
        "city_id": "6173331",
        "sunrise": "2026-10-10T07:26", "sunset": "2026-10-10T18:32",
        "moonrise": "2026-10-10T07:45", "moonset": "2026-10-10T18:05",
        "tithi_end": "2026-10-10T08:49", "nakshatra_end": "2026-10-10T09:12",
        "rahu_kalam": ("2026-10-10T10:13", "2026-10-10T11:36"),
        "yamaganda": ("2026-10-10T14:22", "2026-10-10T15:46"),
        "gulika_kalam": ("2026-10-10T07:26", "2026-10-10T08:49"),
        "abhijit_muhurta": ("2026-10-10T12:37", "2026-10-10T13:21"),
        "brahma_muhurta": ("2026-10-10T05:43", "2026-10-10T06:35"),
    },
    "mumbai": {
        "city_id": "1275339",
        "sunrise": "2026-10-10T06:31", "sunset": "2026-10-10T18:20",
        "moonrise": None,  # Drik shows "No Moonrise" on this Amavasya (Moon next to Sun)
        "moonset": "2026-10-10T17:56",
        "tithi_end": "2026-10-10T21:19", "nakshatra_end": "2026-10-10T21:42",
        "rahu_kalam": ("2026-10-10T09:28", "2026-10-10T10:57"),
        "yamaganda": ("2026-10-10T13:54", "2026-10-10T15:22"),
        "gulika_kalam": ("2026-10-10T06:31", "2026-10-10T08:00"),
        "abhijit_muhurta": ("2026-10-10T12:02", "2026-10-10T12:49"),
        "brahma_muhurta": ("2026-10-10T04:54", "2026-10-10T05:42"),
    },
}  # fmt: skip

TIMING_IDS = ("rahu_kalam", "yamaganda", "gulika_kalam", "abhijit_muhurta", "brahma_muhurta")
MOON_TOLERANCE_MIN = 2


@pytest.fixture(scope="module", params=sorted(REFERENCE))
def case(request, daily):
    ref = REFERENCE[request.param]
    return ref, daily(DATE, city_id=ref["city_id"])


def test_sunrise_and_sunset(case):
    ref, body = case
    assert minutes_apart(body["sun"]["sunrise"]["time"], ref["sunrise"]) <= 1
    assert minutes_apart(body["sun"]["sunset"]["time"], ref["sunset"]) <= 1


def test_element_names_at_sunrise(case):
    _, body = case
    assert body["tithi"]["at_sunrise"]["id"] == "krishna-amavasya"
    assert body["nakshatra"]["at_sunrise"]["name"] == "Hasta"
    assert body["yoga"]["at_sunrise"]["name"] == "Indra"


def test_element_end_times(case):
    ref, body = case
    assert minutes_apart(body["tithi"]["at_sunrise"]["end"], ref["tithi_end"]) <= 1
    assert minutes_apart(body["nakshatra"]["at_sunrise"]["end"], ref["nakshatra_end"]) <= 1


def test_timings(case):
    ref, body = case
    timings = {t["id"]: t for t in body["timings"]}
    for timing_id in TIMING_IDS:
        start, end = ref[timing_id]
        assert minutes_apart(timings[timing_id]["start"], start) <= 1, timing_id
        assert minutes_apart(timings[timing_id]["end"], end) <= 1, timing_id


def test_moonset(case):
    ref, body = case
    assert minutes_apart(body["moon"]["moonset"]["time"], ref["moonset"]) <= MOON_TOLERANCE_MIN


def test_moonrise(case):
    ref, body = case
    moonrise = body["moon"]["moonrise"]
    if ref["moonrise"] is None:
        # Moonrise ~06:0x IST is before sunrise; the next (06:59 Oct 11) is after the next
        # sunrise, so there is none within the Panchang day.
        assert moonrise["status"] == "no_event"
        assert moonrise["time"] is None
    else:
        assert minutes_apart(moonrise["time"], ref["moonrise"]) <= MOON_TOLERANCE_MIN


def test_moonrise_after_midnight_belongs_to_previous_panchang_day(daily):
    # Drik Panchang, Mumbai 2026-11-03: moonrise 02:12 AM on Nov 4 (re-read 2026-10-17; the
    # 02:08 noted earlier was that day's moonset, 02:08 PM).
    moonrise = daily("2026-11-03", city_id="1275339")["moon"]["moonrise"]
    assert moonrise["status"] == "occurs"
    assert minutes_apart(moonrise["time"], "2026-11-04T02:12") <= 1
