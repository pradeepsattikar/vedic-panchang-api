"""Shubh Yogas and Sade Teen Muhurat against Drik Panchang (New Delhi, 2026)."""

from datetime import date, datetime, timedelta

import pytest

from tests.data import drik_shubh_delhi_2026 as drik
from vedic_panchang.domain.location import Location
from vedic_panchang.domain.panchang.calculator import calculate_daily_panchang
from vedic_panchang.rules.profiles import load_profiles

DELHI = Location(28.63576, 77.22445, "Asia/Kolkata", 216)
TOLERANCE_MIN = 3

# Known differences, each explained:
# - Amrit Siddhi 2026-04-21: same times (02:08 to sunrise); Drik prints the end as Apr 22, but
#   the Moon has left Mrigashira by then, so the window is Apr 21 02:08-05:49 (Monday's day).
# - Ravi Yoga 2026-10-24: ends at the Sun's move into Swati, ~6 min earlier than Drik: the same
#   Lahiri-variant gap as Sankranti moments (open item, D05).
KNOWN = {
    "amrit-siddhi": {("2026-04-21", "02:08")},
    "ravi-yoga": {("2026-10-24", "06:27")},
}


@pytest.fixture(scope="module")
def windows():
    profile = load_profiles().get(None)
    out: dict[str, list] = {}
    day = date(2025, 12, 31)
    while day <= date(2027, 1, 1):
        for y in calculate_daily_panchang(day, DELHI, profile).shubh_yogas:
            out.setdefault(y.id, []).append((day, y.start, y.end))
        day += timedelta(days=1)
    return out


def _minutes(hhmm: str) -> int:
    return int(hhmm[:2]) * 60 + int(hhmm[3:])


CASES = [
    ("guru-pushya", drik.GURU_PUSHYA, (date(2026, 1, 1), date(2026, 12, 31))),
    ("ravi-pushya", drik.RAVI_PUSHYA, (date(2026, 1, 1), date(2026, 12, 31))),
    ("amrit-siddhi", drik.AMRIT_SIDDHI, (date(2026, 1, 1), date(2026, 12, 31))),
    ("dwipushkar", drik.DWIPUSHKAR, (date(2026, 1, 1), date(2026, 12, 31))),
    ("tripushkar", drik.TRIPUSHKAR, (date(2026, 1, 1), date(2026, 12, 31))),
    ("sarvartha-siddhi", drik.SARVARTHA_SIDDHI_OCTOBER, (date(2026, 10, 1), date(2026, 10, 31))),
    ("ravi-yoga", drik.RAVI_YOGA_OCTOBER, (date(2026, 10, 1), date(2026, 10, 31))),
]


@pytest.mark.parametrize(("yoga", "rows", "span"), CASES, ids=[c[0] for c in CASES])
def test_matches_drik(windows, yoga, rows, span):
    ours = [w for w in windows.get(yoga, []) if span[0] <= w[0] <= span[1]]
    known = KNOWN.get(yoga, set())
    used: set[int] = set()
    for listed, start, end_day, end in rows:
        if (listed, start) in known:
            continue
        drik_end = datetime.fromisoformat(f"{end_day}T{end}")
        for i, (_, s, e) in enumerate(ours):
            off_end = abs((e.replace(tzinfo=None) - drik_end).total_seconds()) / 60
            off_start = abs(s.hour * 60 + s.minute - _minutes(start))
            if (
                i not in used
                and off_end <= TOLERANCE_MIN
                and min(off_start, 1440 - off_start) <= TOLERANCE_MIN
            ):
                used.add(i)
                break
        else:
            pytest.fail(f"{yoga}: Drik window {listed} {start}-{end_day} {end} not found")
    assert len(ours) - len(used) == len(known), "windows Drik does not list"


def test_daily_answer_lists_yogas_and_sade_teen(daily):
    body = daily("2026-10-20", lat=28.63576, lon=77.22445, tz="Asia/Kolkata")
    assert [y["id"] for y in body["shubh_yogas"]] == ["ravi-yoga"]
    assert body["shubh_rule_version"]
    dussehra = next(o for o in body["observances"] if o["festival_id"] == "dussehra")
    assert dussehra["sade_teen_muhurat"] == "full"


@pytest.mark.parametrize(
    ("festival", "kind"),
    [("chaitra-navratri", "full"), ("akshaya-tritiya", "full"), ("dussehra", "full"),
     ("govardhan-puja", "half"), ("diwali", None)],
)  # fmt: skip
def test_sade_teen_muhurat_days(client, festival, kind):
    body = client.get("/v1/festivals", params={"year": 2026, "city_id": "1261481"}).json()
    item = next(f for f in body["festivals"] if f["festival_id"] == festival)
    assert item["sade_teen_muhurat"] == kind
