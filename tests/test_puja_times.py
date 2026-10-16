"""Puja / observance times (muhurtas) against Drik Panchang.

References are Drik Panchang festival pages (times shown rounded to the minute).
Known gaps, not tested here: moonrise-based times can differ by 4-6 minutes (lunar
parallax, see CLAUDE.md); Sankranti moments are ~8 minutes earlier than Drik's (Lahiri
variant, open question); Drik's Raksha Bandhan page rounds Bhadra's end (1:30 PM) where its
own daily Panchang shows 1:32 PM, as we do.
"""

from datetime import date, timedelta

import pytest

from tests.conftest import minutes_apart

DELHI = {"lat": 28.65195, "lon": 77.23149, "tz": "Asia/Kolkata"}  # GeoNames 1273294
NEW_DELHI = {"lat": 28.63576, "lon": 77.22445, "tz": "Asia/Kolkata"}  # GeoNames 1261481
BRAMPTON = {"lat": 43.6834, "lon": -79.7663, "tz": "America/Toronto", "alt": 218}

# (place, festival, date, muhurta, start, end) — end on the next day where it is earlier.
DRIK = [
    (BRAMPTON, "shukla-pradosh", "2026-10-23", "pradosh", "18:23", "21:03"),  # founder-checked
    (DELHI, "diwali", "2025-10-20", "lakshmi_puja", "19:08", "20:18"),
    (DELHI, "diwali", "2025-10-20", "pradosh", "17:46", "20:18"),
    (DELHI, "diwali", "2025-10-20", "nishita", "23:41", "00:31"),
    (DELHI, "dhanteras", "2025-10-18", "dhanteras_puja", "19:15", "20:19"),
    (DELHI, "dussehra", "2025-10-02", "vijay", "14:09", "14:56"),
    (DELHI, "dussehra", "2025-10-02", "aparahna", "13:21", "15:44"),
    (DELHI, "sharad-navratri", "2025-09-22", "ghatasthapana_kanya", "06:09", "08:06"),
    (DELHI, "sharad-navratri", "2025-09-22", "abhijit", "11:49", "12:38"),
    (DELHI, "chaitra-navratri", "2025-03-30", "ghatasthapana", "06:13", "10:22"),
    (DELHI, "govardhan-puja", "2025-10-22", "pratahkala", "06:26", "08:42"),
    (DELHI, "govardhan-puja", "2025-10-22", "sayankala", "15:29", "17:44"),
    (DELHI, "karwa-chauth", "2026-10-29", "sandhya_puja", "17:38", "18:56"),
    (DELHI, "krishna-janmashtami", "2025-08-15", "nishita", "00:04", "00:47"),
    (NEW_DELHI, "ahoi-ashtami", "2025-10-13", "sandhya_puja", "17:53", "19:08"),
    (NEW_DELHI, "ahoi-ashtami", "2025-10-13", "star_sighting", "18:17", "18:17"),
    (NEW_DELHI, "anant-chaturdashi", "2026-09-25", "tithi_daytime", "06:11", "23:06"),
    (NEW_DELHI, "ganesh-chaturthi", "2025-08-27", "madhyahna", "11:05", "13:40"),
    (NEW_DELHI, "vasant-panchami", "2025-02-02", "purvahna", "07:09", "12:35"),
    (NEW_DELHI, "akshaya-tritiya", "2025-04-30", "purvahna", "05:41", "12:18"),
    (NEW_DELHI, "hartalika-teej", "2025-08-26", "pratahkala", "05:56", "08:31"),
    (NEW_DELHI, "ram-navami", "2025-04-06", "madhyahna", "11:08", "13:39"),
    (NEW_DELHI, "bhai-dooj", "2025-10-23", "aparahna", "13:13", "15:28"),
    (NEW_DELHI, "maha-shivaratri", "2025-02-26", "nishita", "00:09", "00:59"),
    (NEW_DELHI, "maha-shivaratri", "2025-02-26", "prahar_1", "18:19", "21:26"),
    (NEW_DELHI, "sharad-purnima", "2025-10-06", "nishita", "23:45", "00:34"),
    (NEW_DELHI, "yogini-ekadashi", "2025-06-21", "parana", "13:47", "16:35"),  # Jun 22
    (NEW_DELHI, "pausha-putrada-ekadashi", "2025-12-30", "parana", "13:26", "15:31"),  # Dec 31
]  # fmt: skip

NEXT_DAY = {"parana"}  # on the day after the observance date
NIGHT = {"nishita"}  # a morning clock time means after midnight


@pytest.fixture(scope="module")
def festivals(client):
    cache: dict = {}

    def fetch(place: dict, year: int) -> list[dict]:
        key = (place["lat"], year)
        if key not in cache:
            response = client.get("/v1/festivals", params={"year": year, **place})
            assert response.status_code == 200, response.text
            cache[key] = response.json()["festivals"]
        return cache[key]

    return fetch


def _puja(festivals, place, festival_id, day, muhurta) -> dict:
    occurrence = next(
        f
        for f in festivals(place, int(day[:4]))
        if f["festival_id"] == festival_id and f["date"] == day
    )
    return next(p for p in occurrence["puja_times"] if p["id"] == muhurta)


def _at(day: date, time: str) -> str:
    return f"{day.isoformat()}T{time}"


@pytest.mark.parametrize(("place", "festival_id", "day", "muhurta", "start", "end"), DRIK)
def test_puja_time_matches_drik(festivals, place, festival_id, day, muhurta, start, end):
    puja = _puja(festivals, place, festival_id, day, muhurta)
    start_day = date.fromisoformat(day)
    if muhurta in NEXT_DAY or (muhurta in NIGHT and start < "12:00"):
        start_day += timedelta(days=1)
    end_day = start_day + timedelta(days=1 if end < start else 0)
    assert minutes_apart(puja["start"], _at(start_day, start)) <= 1
    assert minutes_apart(puja["end"], _at(end_day, end)) <= 1


def test_holika_dahan_after_bhadra_until_midnight(festivals):
    # Drik 2025-03-13: Bhadra 10:35 AM-11:26 PM covers Pradosh -> 11:26 PM-12:30 AM.
    # Our Bhadra ends at 11:27:43 PM (Tithi/Karana boundaries run ~1-1.5 min later than
    # Drik's on this date), hence 2 minutes here.
    puja = _puja(festivals, DELHI, "holika-dahan", "2025-03-13", "holika_dahan")
    assert minutes_apart(puja["start"], "2025-03-13T23:26") <= 2
    assert minutes_apart(puja["end"], "2025-03-14T00:30") <= 1


def test_instants_and_order(festivals):
    items = festivals(BRAMPTON, 2026)
    karwa = next(f for f in items if f["festival_id"] == "karwa-chauth")
    ids = [p["id"] for p in karwa["puja_times"]]
    assert ids == ["sandhya_puja", "moonrise", "upavasa"]
    moonrise = karwa["puja_times"][1]
    assert moonrise["start"] == moonrise["end"]


def test_no_puja_time_where_none_is_prescribed(festivals):
    items = festivals(BRAMPTON, 2026)
    holi = next(f for f in items if f["festival_id"] == "holi")
    assert holi["puja_times"] == []


def test_every_rule_names_known_muhurtas():
    from vedic_panchang.domain.festivals.muhurta import RECIPES
    from vedic_panchang.rules.festivals import load_festival_set

    festival_set = load_festival_set("north-indian-smarta")
    for rule in (*festival_set.lunar, *festival_set.solar):
        assert set(rule.puja) <= set(RECIPES), (rule.id, rule.puja)
