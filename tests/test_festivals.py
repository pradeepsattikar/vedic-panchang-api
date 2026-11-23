"""Festival dates (EN-18).

Reference dates are New Delhi dates from published 2024-2026 festival calendars that
follow the North Indian Smarta convention. Dates for other cities can correctly differ.
Holika Dahan 2026 is excluded: published calendars disagree (2 vs 3 March), pending a
Drik Panchang check.
"""

import pytest

DELHI = {"lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata", "alt": 216}
TORONTO = {"city_id": "6167865"}

PUBLISHED_DELHI = {
    2024: {
        "makar-sankranti": "2024-01-15", "maha-shivaratri": "2024-03-08",
        "holika-dahan": "2024-03-24", "holi": "2024-03-25", "ram-navami": "2024-04-17",
        "akshaya-tritiya": "2024-05-10", "guru-purnima": "2024-07-21",
        "raksha-bandhan": "2024-08-19", "krishna-janmashtami": "2024-08-26",
        "ganesh-chaturthi": "2024-09-07", "dussehra": "2024-10-12",
        "karwa-chauth": "2024-10-20", "dhanteras": "2024-10-29", "diwali": "2024-10-31",
        "govardhan-puja": "2024-11-02", "bhai-dooj": "2024-11-03", "chhath-puja": "2024-11-07",
    },
    2025: {
        "makar-sankranti": "2025-01-14", "maha-shivaratri": "2025-02-26",
        "holika-dahan": "2025-03-13", "holi": "2025-03-14", "ram-navami": "2025-04-06",
        "akshaya-tritiya": "2025-04-30", "guru-purnima": "2025-07-10",
        "raksha-bandhan": "2025-08-09", "ganesh-chaturthi": "2025-08-27",
        "dussehra": "2025-10-02", "karwa-chauth": "2025-10-10", "dhanteras": "2025-10-18",
        "diwali": "2025-10-20", "govardhan-puja": "2025-10-22", "bhai-dooj": "2025-10-23",
        "chhath-puja": "2025-10-27",
    },
    2026: {
        "makar-sankranti": "2026-01-14", "holi": "2026-03-04", "raksha-bandhan": "2026-08-28",
        "durga-ashtami": "2026-10-19", "maha-navami": "2026-10-20", "dussehra": "2026-10-20",
        "diwali": "2026-11-08", "naraka-chaturdashi": "2026-11-08",
        "govardhan-puja": "2026-11-09", "bhai-dooj": "2026-11-11",
    },
}  # fmt: skip


@pytest.fixture(scope="module")
def festivals(client):
    def fetch(year: int, **params) -> list[dict]:
        response = client.get("/v1/festivals", params={"year": year, **params})
        assert response.status_code == 200, response.text
        return response.json()["festivals"]

    return fetch


@pytest.mark.parametrize("year", sorted(PUBLISHED_DELHI))
def test_published_delhi_dates(festivals, year):
    dates = {f["festival_id"]: f["date"] for f in festivals(year, **DELHI)}
    mismatches = {
        fid: (dates.get(fid), expected)
        for fid, expected in PUBLISHED_DELHI[year].items()
        if dates.get(fid) != expected
    }
    assert not mismatches, mismatches


def test_occurrence_carries_tithi_masa_and_kala(festivals):
    diwali = next(f for f in festivals(2026, **DELHI) if f["festival_id"] == "diwali")
    assert diwali["name"] == "Diwali (Lakshmi Puja)"
    assert diwali["short_name"] == "Diwali"
    assert diwali["category"] == "major"
    assert diwali["kala"] == "pradosh"
    assert diwali["tithi"]["id"] == "krishna-amavasya"
    assert diwali["masa"]["purnimanta"]["id"] == "kartika"
    assert diwali["masa"]["amanta"]["id"] == "ashwin"


def test_monthly_names_use_purnimanta_months(festivals):
    names = {
        f["date"]: f["name"] for f in festivals(2026, **DELHI) if f["festival_id"] == "amavasya"
    }
    assert names["2026-01-18"] == "Magha Amavasya"  # Mauni Amavasya


def test_adhika_only_ekadashis_appear_only_in_adhika_years(festivals):
    ids_2026 = [f["festival_id"] for f in festivals(2026, **DELHI)]
    ids_2025 = [f["festival_id"] for f in festivals(2025, **DELHI)]
    for fid in ("padmini-ekadashi", "parama-ekadashi"):
        assert ids_2026.count(fid) == 1  # 2026 has Adhika Jyeshtha
        assert fid not in ids_2025


def test_counts_per_year(festivals):
    ids = [f["festival_id"] for f in festivals(2025, **DELHI)]
    assert ids.count("purnima") == 12
    assert ids.count("amavasya") == 12
    assert ids.count("sankranti") + ids.count("makar-sankranti") == 12
    assert ids.count("masik-shivaratri") == 11  # Magha's is Maha Shivaratri
    assert "Makara Sankranti" not in {f["name"] for f in festivals(2025, **DELHI)}


def test_sankranti_after_sunset_moves_to_next_day(festivals):
    for f in festivals(2025, **DELHI):
        if f["sankranti_time"] and f["festival_id"] != "lohri":  # Lohri is the eve
            assert f["date"] >= f["sankranti_time"][:10]


def test_occurrence_ids_are_stable_across_places(festivals):
    delhi = {f["festival_id"]: f for f in festivals(2026, **DELHI)}
    toronto = {f["festival_id"]: f for f in festivals(2026, **TORONTO)}
    assert delhi["diwali"]["occurrence_id"] == toronto["diwali"]["occurrence_id"]
    # Same Tithi instant, different local day: correct and expected.
    assert delhi["karwa-chauth"]["date"] == "2026-10-29"
    assert toronto["karwa-chauth"]["date"] == "2026-10-28"


def test_daily_response_lists_observances(daily):
    observances = daily("2026-11-08", **DELHI)["observances"]
    assert {o["festival_id"] for o in observances} == {"diwali", "naraka-chaturdashi"}
    assert observances[0]["category"] == "major"
    # Amavasya begins 11:28 on Nov 8, so it prevails at sunrise only on Nov 9.
    next_day = daily("2026-11-09", **DELHI)["observances"]
    assert [o["name"] for o in next_day if o["festival_id"] == "amavasya"] == ["Kartika Amavasya"]


def test_single_festival_endpoint_and_category_filter(client):
    body = client.get("/v1/festivals/diwali", params={"year": 2026, **DELHI}).json()
    assert [f["date"] for f in body["festivals"]] == ["2026-11-08"]
    assert body["festival_rule_version"]
    major = client.get("/v1/festivals", params={"year": 2026, "category": "major", **DELHI})
    assert {f["category"] for f in major.json()["festivals"]} == {"major"}


@pytest.mark.parametrize(
    ("path", "params", "status", "code"),
    [
        ("/v1/festivals/no-such-day", {"year": 2026}, 404, "festival_not_found"),
        ("/v1/festivals", {"year": 2019}, 422, "date_out_of_range"),
        ("/v1/festivals", {"year": 2026, "category": "minor"}, 422, "invalid_request"),
    ],
)
def test_festival_errors(client, path, params, status, code):
    response = client.get(path, params={**params, **DELHI})
    assert response.status_code == status
    assert response.json()["error"]["code"] == code


def test_every_short_name_fits_a_calendar_cell(festivals):
    short_names = {f["short_name"] for y in (2025, 2026) for f in festivals(y, **DELHI)}
    assert "Durga Asht." in short_names and "Ekadashi" in short_names
    assert all(0 < len(name) <= 13 for name in short_names), sorted(short_names, key=len)[-3:]


# Dev Deepawali: lamps at dusk, so Purnima must prevail in Pradosh (not at sunrise).
# Drik Panchang "Dev Diwali" dates, checked Nov 19, 2026.
DEV_DEEPAWALI_DRIK = [
    ("6167865", 2026, "2026-11-23"),  # Toronto: Purnima ends Nov 24 9:54 AM, so Monday's dusk
    ("6167865", 2025, "2025-11-04"),  # Toronto
    ("5368361", 2025, "2025-11-04"),  # Los Angeles
    ("5946768", 2026, "2026-11-23"),  # Edmonton
    ("1253405", 2026, "2026-11-24"),  # Varanasi: Purnima lasts until 8:23 PM on Nov 24
    ("1273294", 2027, "2027-11-13"),  # New Delhi: a day before the sunrise Purnima
    ("1275339", 2028, "2028-11-01"),  # Mumbai
]


@pytest.mark.parametrize(("city_id", "year", "expected"), DEV_DEEPAWALI_DRIK)
def test_dev_deepawali_follows_purnima_at_pradosh(festivals, city_id, year, expected):
    dates = {f["festival_id"]: f["date"] for f in festivals(year, city_id=city_id)}
    assert dates["kartik-purnima"] == expected


def test_shiv_jayanti_official_date_and_tithi(client):
    # Official (Maharashtra Government) date is fixed at 19 February; the Tithi date is
    # Phalguna Krishna Tritiya at sunrise: Pune 6 Mar 2026 (Tritiya 5 Mar 17:04 - 6 Mar 17:53 IST),
    # Toronto 5 Mar 2026 (Tritiya begins 06:34 EST, before sunrise).
    def dates(city_id, year):
        params = {"city_id": city_id, "year": year, "include_extended": "true"}
        body = client.get("/v1/festivals", params=params).json()
        return {
            f["festival_id"]: f["date"]
            for f in body["festivals"]
            if f["festival_id"].startswith("shiv-jayanti")
        }

    assert dates("1259229", 2026) == {
        "shiv-jayanti": "2026-02-19",
        "shiv-jayanti-tithi": "2026-03-06",
    }
    assert dates("6167865", 2026) == {
        "shiv-jayanti": "2026-02-19",
        "shiv-jayanti-tithi": "2026-03-05",
    }
    assert dates("1259229", 2025)["shiv-jayanti-tithi"] == "2025-03-17"


def test_gta_regional_festivals_2026(client):
    # Rules added 2026-11-23 for the printed Toronto Panchang; dates from the API, to be checked
    # against Drik / regional calendars before print. Guards against accidental rule changes.
    params = {"city_id": "1261481", "year": 2026, "include_extended": "true"}
    body = client.get("/v1/festivals", params=params).json()
    got = {f["festival_id"]: f["date"] for f in body["festivals"]}
    assert got["sheetala-ashtami"] == "2026-03-11"
    assert got["vat-purnima"] == "2026-06-29"
    assert got["shitala-satam"] == "2026-09-03"  # day before Janmashtami (4 Sep)
    assert got["kali-puja"] == "2026-11-08"
    assert got["labh-pancham"] == "2026-11-14"
    assert got["jalaram-jayanti"] == "2026-11-16"


def test_extended_festivals_only_on_request(client, daily):
    # Founder 2026-11-23: festivals not yet in the app stay out of the default answers.
    city = {"city_id": "1261481"}
    default = client.get("/v1/festivals", params={**city, "year": 2026}).json()["festivals"]
    extended = client.get(
        "/v1/festivals", params={**city, "year": 2026, "include_extended": "true"}
    ).json()["festivals"]
    assert not any(f["extended"] for f in default)
    assert {"kali-puja", "tulsi-vivah", "shiv-jayanti"} <= {f["festival_id"] for f in extended}
    # daily and month follow the same switch
    ids = {o["festival_id"] for o in daily("2026-11-08", **city)["observances"]}
    assert "kali-puja" not in ids
    ids = {
        o["festival_id"]
        for o in daily("2026-11-08", **city, include_extended="true")["observances"]
    }
    assert "kali-puja" in ids
    month = client.get(
        "/v1/panchang/month",
        params={**city, "year": 2026, "month": 11, "include_extended": "true"},
    ).json()
    assert any(o["festival_id"] == "kali-puja" for d in month["days"] for o in d["observances"])
    # asking for one festival by id always answers
    one = client.get("/v1/festivals/kali-puja", params={**city, "year": 2026})
    assert one.status_code == 200 and one.json()["festivals"][0]["date"] == "2026-11-08"
