"""General muhurtas against Drik Panchang's 2026 lists for Ottawa (tests/data/).

Known differences, kept out of the comparison (Drik's own inconsistencies or unmodelled rules):
- Vivah 2026-03-08: Drik's window covers Vishakha (not a Vivah Nakshatra) on the day the clocks
  change; every other Vishakha time is excluded by Drik too.
- Vivah 2026-04-20 (Panchang day; 03:02-06:07 on Apr 21): Drik allows the start of Atiganda Yoga
  here only.
- Vivah 2026-04-14: we give 24 minutes before sunrise on Mesha Sankranti day; Drik gives none.
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from tests.data.drik_muhurta_ottawa_2026 import GRIHA_PRAVESH, VIVAH
from vedic_panchang.astronomy.ephemeris import Ayanamsha
from vedic_panchang.domain.location import Location
from vedic_panchang.domain.muhurta.engine import muhurta_windows
from vedic_panchang.rules.muhurta import load_muhurta_rules

TZ = ZoneInfo("America/Toronto")
OTTAWA = Location(latitude=45.41117, longitude=-75.69812, timezone="America/Toronto", altitude_m=71)
KNOWN = {"vivah": {"2026-03-08", "2026-04-14", "2026-04-20"}, "griha-pravesh": set()}


def _minutes(day: str, start: str, end: str) -> set[int]:
    def at(value: str) -> int:
        later = value.endswith("+1")
        hour, minute = map(int, value.removesuffix("+1").split(":"))
        moment = datetime.fromisoformat(day).replace(tzinfo=TZ) + timedelta(days=int(later))
        return int(moment.replace(hour=hour, minute=minute).timestamp() // 60)

    return set(range(at(start), at(end)))


@pytest.fixture(scope="module", params=[("vivah", VIVAH), ("griha-pravesh", GRIHA_PRAVESH)],
                ids=["vivah", "griha-pravesh"])  # fmt: skip
def comparison(request):
    purpose_id, drik = request.param
    rules = load_muhurta_rules()
    windows = muhurta_windows(rules.purpose(purpose_id), rules, OTTAWA, Ayanamsha.LAHIRI,
                              date(2026, 1, 1), date(2026, 12, 31))  # fmt: skip
    known = KNOWN[purpose_id]
    ours = {w for w in windows if w.day.isoformat() not in known}
    theirs = [d for d in drik if d[0] not in known]
    return purpose_id, ours, theirs


def test_same_days_as_drik(comparison):
    _, ours, theirs = comparison
    assert {w.day.isoformat() for w in ours} == {d[0] for d in theirs}


def test_windows_match_drik_to_the_minute(comparison):
    _, ours, theirs = comparison
    drik = set().union(*(_minutes(*d) for d in theirs))
    mine = set()
    for w in ours:
        mine.update(range(round(w.start.timestamp() / 60), round(w.end.timestamp() / 60)))
    assert len(drik & mine) / len(drik) > 0.995, (len(drik - mine), len(mine - drik))
    assert len(mine - drik) / len(drik) < 0.005


def test_windows_are_split_at_sunrise_and_named(comparison):
    _, ours, _ = comparison
    for w in ours:
        assert w.start < w.end and w.nakshatras and w.tithis
        assert (w.end - w.start).total_seconds() >= 5 * 60


def test_api(client):
    purposes = client.get("/v1/muhurta/purposes").json()
    assert [p["id"] for p in purposes] == ["vivah", "griha-pravesh"]
    body = client.get(
        "/v1/muhurta",
        params={"purpose": "griha-pravesh", "city_id": "6094817", "from": "2026-11-01", "days": 30},
    ).json()
    assert body["basis"].startswith("General Panchang Shuddhi")
    days = [w["day"] for w in body["windows"]]
    assert days[:3] == ["2026-11-09", "2026-11-14", "2026-11-19"]
    missing = client.get("/v1/muhurta", params={"purpose": "mundan", "city_id": "6094817"})
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "purpose_not_found"
