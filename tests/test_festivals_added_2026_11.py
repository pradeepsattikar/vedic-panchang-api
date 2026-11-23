"""Festivals added 2026-11 (founder): dates and puja times checked against Drik Panchang
(read 2026-11-15) for New Delhi and Toronto, 2025-2027.

Known difference, not tested: Baisakhi Toronto 2026. Drik gives 13 April although its own
Sankranti moment is 12:09 AM on 14 April; we keep the ingress's civil date (14 April).
Lohri is checked for 2026 only (Drik's other Lohri pages were blocked by a captcha).
"""

import pytest

CITIES = {"delhi": "1261481", "toronto": "6167865"}

DRIK = {
    "delhi": {
        "parshuram-jayanti": ["2025-04-29", "2026-04-19", "2027-05-08"],
        "sita-navami": ["2025-05-05", "2026-04-25", "2027-05-14"],
        "narasimha-jayanti": ["2025-05-11", "2026-04-30", "2027-05-18"],
        "ganga-dussehra": ["2025-06-05", "2026-05-25", "2027-06-13"],
        "rath-yatra": ["2025-06-27", "2026-07-16", "2027-07-05"],
        "kajari-teej": ["2025-08-12", "2026-08-31", "2027-08-20"],
        "rishi-panchami": ["2025-08-28", "2026-09-15", "2027-09-04"],
        "radha-ashtami": ["2025-08-31", "2026-09-19", "2027-09-08"],
        "gopashtami": ["2025-10-30", "2026-11-17", "2027-11-06"],
        "akshaya-navami": ["2025-10-31", "2026-11-18", "2027-11-07"],
        "kansa-vadh": ["2025-11-01", "2026-11-20", "2027-11-08"],
        "bhishma-panchak": ["2025-11-01"],
        "tulsi-vivah": ["2025-11-02", "2026-11-21", "2027-11-11"],
        "vaikuntha-chaturdashi": ["2025-11-04", "2026-11-23", "2027-11-12"],
        "lohri": ["2026-01-13"],
        "baisakhi": ["2025-04-14", "2026-04-14", "2027-04-14"],
        "vishwakarma-puja": ["2025-09-17", "2026-09-17", "2027-09-17"],
    },
    "toronto": {
        "parshuram-jayanti": ["2025-04-29", "2026-04-19", "2027-05-08"],
        "sita-navami": ["2025-05-05", "2026-04-24", "2027-05-14"],
        "narasimha-jayanti": ["2025-05-10", "2026-04-29", "2027-05-18"],
        "ganga-dussehra": ["2025-06-05", "2026-05-25", "2027-06-13"],
        "rath-yatra": ["2025-06-26", "2026-07-15", "2027-07-05"],
        "kajari-teej": ["2025-08-11", "2026-08-30", "2027-08-20"],
        "rishi-panchami": ["2025-08-27", "2026-09-15", "2027-09-04"],
        "radha-ashtami": ["2025-08-31", "2026-09-18", "2027-09-07"],
        "gopashtami": ["2025-10-29", "2026-11-17", "2027-11-06"],
        "akshaya-navami": ["2025-10-30", "2026-11-18", "2027-11-07"],
        "kansa-vadh": ["2025-10-31", "2026-11-19", "2027-11-08"],
        "bhishma-panchak": ["2026-11-20"],
        "tulsi-vivah": ["2025-11-02", "2026-11-21", "2027-11-10"],
        "vaikuntha-chaturdashi": ["2025-11-03", "2026-11-22", "2027-11-11"],
        "lohri": ["2026-01-13"],
        "baisakhi": ["2025-04-13", "2027-04-14"],
        "vishwakarma-puja": ["2025-09-16", "2026-09-16", "2027-09-17"],
    },
}

# (city, festival, date, first puja window "HH:MM"-"HH:MM" local) from Drik; ±1 minute.
PUJA = [
    ("delhi", "akshaya-navami", "2025-10-31", "06:32", "10:03"),
    ("delhi", "vaikuntha-chaturdashi", "2026-11-23", "23:41", "00:35"),
    ("delhi", "radha-ashtami", "2027-09-08", "11:03", "13:34"),
    ("delhi", "narasimha-jayanti", "2025-05-11", "16:21", "19:03"),
    ("delhi", "sita-navami", "2025-05-05", "10:58", "13:38"),
    ("delhi", "rishi-panchami", "2027-09-04", "12:25", "13:36"),
    ("toronto", "sita-navami", "2027-05-14", "11:46", "14:42"),
    ("toronto", "narasimha-jayanti", "2026-04-29", "17:29", "20:18"),
    ("toronto", "vaikuntha-chaturdashi", "2027-11-11", "23:50", "00:30"),
    ("toronto", "akshaya-navami", "2026-11-18", "07:16", "12:03"),
]


@pytest.fixture(scope="module")
def dates_by_year(client):
    cache: dict = {}

    def fetch(city: str, year: int) -> dict[str, list[dict]]:
        if (city, year) not in cache:
            params = {"city_id": CITIES[city], "year": year, "include_extended": "true"}
            response = client.get("/v1/festivals", params=params)
            assert response.status_code == 200, response.text
            found: dict[str, list[dict]] = {}
            for item in response.json()["festivals"]:
                found.setdefault(item["festival_id"], []).append(item)
            cache[(city, year)] = found
        return cache[(city, year)]

    return fetch


@pytest.mark.parametrize("city", sorted(DRIK))
def test_dates_match_drik(dates_by_year, city):
    mismatches = {}
    for festival, expected in DRIK[city].items():
        for day in expected:
            got = [f["date"] for f in dates_by_year(city, int(day[:4])).get(festival, [])]
            if day not in got:
                mismatches[(festival, day)] = got
    assert not mismatches, mismatches


def _minutes(hhmm: str) -> int:
    hours, minutes = map(int, hhmm.split(":"))
    return hours * 60 + minutes


@pytest.mark.parametrize(("city", "festival", "day", "start", "end"), PUJA)
def test_puja_window_matches_drik(dates_by_year, city, festival, day, start, end):
    [item] = [f for f in dates_by_year(city, int(day[:4]))[festival] if f["date"] == day]
    window = item["puja_times"][0]
    for got, want in ((window["start"][11:16], start), (window["end"][11:16], end)):
        assert abs(_minutes(got) - _minutes(want)) % 1439 <= 1, (window, start, end)
