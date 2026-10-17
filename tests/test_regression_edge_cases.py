"""Edge-case regression suite (EN-20): DST, midnight boundaries, no-event days, polar
regions, unusual timezones and leap dates.

Expected values are the engine's own verified outputs (cross-checked across cities in UTC
and against the boundary/DST/no-moonrise verification runs of 2026-10-12). They guard
against regressions; Drik Panchang reference checks live in test_reference_drik.py.
"""

from datetime import UTC, datetime

import pytest

from tests.conftest import minutes_apart

TORONTO = {"city_id": "6167865"}
VANCOUVER = {"city_id": "6173331"}
MUMBAI = {"city_id": "1275339"}
ST_JOHNS = {"city_id": "6324733"}  # UTC-3:30 / -2:30
PHOENIX = {"city_id": "5308655"}  # no DST
LONDON = {"lat": 51.5074, "lon": -0.1278, "tz": "Europe/London", "alt": 11}
UTQIAGVIK = {"lat": 71.2906, "lon": -156.7886, "tz": "America/Anchorage"}  # polar night


def utc(iso_time: str) -> datetime:
    return datetime.fromisoformat(iso_time).astimezone(UTC).replace(second=0)


parse = datetime.fromisoformat


def offset(iso_time: str) -> str:
    minutes = int(parse(iso_time).utcoffset().total_seconds() // 60)
    sign = "+" if minutes >= 0 else "-"
    return f"{sign}{abs(minutes) // 60:02d}:{abs(minutes) % 60:02d}"


# ── Midnight boundary (D04) ──────────────────────────────────────────────────────


def test_tithi_ending_after_midnight_carries_next_date(daily):
    body = daily("2026-11-02", **TORONTO)
    tithi = body["tithi"]["at_sunrise"]
    assert tithi["id"] == "krishna-navami"
    assert minutes_apart(tithi["end"], "2026-11-03T01:25") <= 1
    assert tithi["end"].startswith("2026-11-03")


def test_same_transition_is_identical_in_utc_across_cities(daily):
    toronto = daily("2026-11-03", **TORONTO)["tithi"]["at_sunrise"]
    vancouver = daily("2026-11-03", **VANCOUVER)["tithi"]["at_sunrise"]
    assert toronto["id"] == vancouver["id"] == "krishna-dashami"
    assert utc(toronto["end"]) == utc(vancouver["end"])


def test_cities_can_correctly_differ_in_tithi_at_sunrise(daily):
    # Saptami -> Ashtami at ~09:22 UTC on Nov 1: after Mumbai's sunrise, before Toronto's.
    assert daily("2026-11-01", **MUMBAI)["tithi"]["at_sunrise"]["id"] == "krishna-saptami"
    assert daily("2026-11-01", **TORONTO)["tithi"]["at_sunrise"]["id"] == "krishna-ashtami"


# ── DST transitions ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("place", "day", "expected_offset"),
    [
        (TORONTO, "2026-10-31", "-04:00"),
        (TORONTO, "2026-11-01", "-05:00"),
        # British Columbia adopted permanent daylight time in 2026: no fall-back.
        (VANCOUVER, "2026-10-31", "-07:00"),
        (VANCOUVER, "2026-11-01", "-07:00"),
        (VANCOUVER, "2026-12-15", "-07:00"),
        (LONDON, "2026-10-24", "+01:00"),
        (LONDON, "2026-10-25", "+00:00"),
    ],
)
def test_dst_offset_applied_on_transition_days(daily, place, day, expected_offset):
    body = daily(day, **place)
    for event in ("sunrise", "sunset"):
        assert offset(body["sun"][event]["time"]) == expected_offset
    rahu = next(t for t in body["timings"] if t["id"] == "rahu_kalam")
    assert rahu["start"] < rahu["end"]


def test_dst_fall_back_day_keeps_sane_day_length(daily):
    before = daily("2026-10-31", **TORONTO)["sun"]
    after = daily("2026-11-01", **TORONTO)["sun"]
    length = [
        datetime.fromisoformat(s["sunset"]["time"]) - datetime.fromisoformat(s["sunrise"]["time"])
        for s in (before, after)
    ]
    assert abs((length[0] - length[1]).total_seconds()) < 300  # ~2-3 min shorter, not 1 h


# ── Unusual timezones ────────────────────────────────────────────────────────────


def test_half_hour_offset_newfoundland(daily):
    assert offset(daily("2026-07-01", **ST_JOHNS)["sun"]["sunrise"]["time"]) == "-02:30"
    assert offset(daily("2026-01-15", **ST_JOHNS)["sun"]["sunrise"]["time"]) == "-03:30"


def test_arizona_does_not_observe_dst(daily):
    assert offset(daily("2026-07-01", **PHOENIX)["sun"]["sunrise"]["time"]) == "-07:00"


# ── Moon events within the Panchang day (sunrise to next sunrise, D06) ──────────


@pytest.mark.parametrize(
    ("place", "day", "event", "next_time"),
    [
        (MUMBAI, "2026-10-10", "moonrise", "2026-10-11T06:59"),  # Amavasya
        (LONDON, "2026-11-08", "moonrise", "2026-11-09T07:47"),
        (LONDON, "2026-11-23", "moonset", "2026-11-24T07:36"),
    ],
)
def test_no_moon_event_reports_no_event_with_next_time(daily, place, day, event, next_time):
    result = daily(day, **place)["moon"][event]
    assert result["status"] == "no_event"
    assert result["time"] is None
    assert minutes_apart(result["next_time"], next_time) <= 1


@pytest.mark.parametrize(("day", "expected"), [
    ("2026-11-02", "2026-11-03T01:15"),
    ("2026-11-04", "2026-11-05T03:06"),
])  # fmt: skip
def test_moonrise_before_next_sunrise_carries_next_date(daily, day, expected):
    moonrise = daily(day, **MUMBAI)["moon"]["moonrise"]
    assert moonrise["status"] == "occurs"
    assert minutes_apart(moonrise["time"], expected) <= 1


# ── Polar regions: unavailable, never fabricated ─────────────────────────────────


def test_polar_night_marks_sunrise_values_unavailable(daily):
    body = daily("2026-12-21", **UTQIAGVIK)
    assert body["sun"]["sunrise"]["status"] == "unavailable"
    assert body["sun"]["sunrise"]["time"] is None
    assert body["day_window"]["basis"] == "civil_day"
    for element in ("tithi", "nakshatra", "yoga", "karana"):
        assert body[element]["at_sunrise"] is None
        assert body[element]["unavailable_reason"]
        assert body[element]["spans"]  # spans over the civil day are still real values
    for timing in body["timings"]:
        assert timing["applicable"] is False
        assert timing["start"] is None and timing["end"] is None


# ── Weekday exceptions (D08) ──────────────────────────────────────────────────────


def test_abhijit_muhurta_avoided_on_wednesday(daily):
    timings = {t["id"]: t for t in daily("2026-10-14", **MUMBAI)["timings"]}  # Wednesday
    abhijit = timings["abhijit_muhurta"]
    assert abhijit["applicable"] is False
    assert abhijit["start"] is None and abhijit["end"] is None
    assert "Wednesday" in abhijit["reason"]
    assert timings["rahu_kalam"]["applicable"] is True


def test_abhijit_muhurta_present_on_thursday(daily):
    timings = {t["id"]: t for t in daily("2026-10-15", **MUMBAI)["timings"]}
    assert timings["abhijit_muhurta"]["applicable"] is True


# ── Leap date ────────────────────────────────────────────────────────────────────


def test_leap_day(daily):
    body = daily("2028-02-29", **TORONTO)
    assert body["date"] == "2028-02-29"
    assert body["vara"]["id"] == "mangalavara"  # Tuesday
    assert body["sun"]["sunrise"]["time"].startswith("2028-02-29")


# ── Structural invariants over many days and places ──────────────────────────────


@pytest.mark.parametrize("place", [TORONTO, VANCOUVER, MUMBAI, LONDON, ST_JOHNS])
@pytest.mark.parametrize("day", ["2026-01-01", "2026-03-08", "2026-06-21", "2026-11-05"])
def test_spans_are_contiguous_and_cover_the_panchang_day(daily, place, day):
    body = daily(day, **place)
    window = body["day_window"]
    assert window["basis"] == "sunrise_to_next_sunrise"
    start, end = parse(window["start"]), parse(window["end"])
    for element, cycle in (("tithi", 30), ("nakshatra", 27), ("yoga", 27), ("karana", 60)):
        spans = body[element]["spans"]
        assert parse(spans[0]["start"]) <= start < parse(spans[0]["end"])
        assert parse(spans[-1]["end"]) >= end
        assert body[element]["at_sunrise"] == spans[0]
        for prev, nxt in zip(spans, spans[1:], strict=False):
            assert parse(prev["end"]) == parse(nxt["start"])
            assert nxt["number"] == prev["number"] % cycle + 1
