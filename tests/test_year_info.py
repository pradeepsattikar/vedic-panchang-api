"""Samvat, Ritu, Ayana and Sun/Moon Rashi (preview additions), against Drik Panchang.

Drik, Toronto 2026-10-17: Vikram Samvat 2083, Shaka Samvat 1948, Ritu Sharad, Ayana
Dakshinayana, Sun sign Kanya until 10:27 AM then Tula, Moon sign Dhanu.
"""

from tests.conftest import minutes_apart

TORONTO = {"city_id": "6167865"}
MUMBAI = {"city_id": "1275339"}
PUNE = {"city_id": "1259229"}
MAHARASHTRIAN = {"profile": "maharashtrian-smarta"}


def test_matches_drik_toronto(daily):
    body = daily("2026-10-17", **TORONTO)
    assert body["year"] == {
        "vikram_samvat": 2083,
        "vikram_year_start": "chaitra",
        "shaka_samvat": 1948,
        "vikram_samvatsara": {"number": 53, "id": "siddharthi", "name": "Siddharthi"},
        "shaka_samvatsara": {"number": 40, "id": "parabhava", "name": "Parabhava"},
        "ritu": "Sharad",
        "ayana": "Dakshinayana",
    }
    sun = body["sun_sign"]["spans"]
    assert [s["name"] for s in sun] == ["Kanya", "Tula"]
    # Tula Sankranti: Drik 10:27 AM. Sankranti moments run ~8 min early (Lahiri variant, open).
    assert minutes_apart(sun[0]["end"], "2026-10-17T10:27") <= 10
    assert body["moon_sign"]["at_sunrise"]["name"] == "Dhanu"


def test_samvat_year_boundary(daily):
    assert daily("2026-03-10", **MUMBAI)["year"]["vikram_samvat"] == 2082  # Phalguna
    assert daily("2026-04-10", **MUMBAI)["year"]["vikram_samvat"] == 2083  # Chaitra
    assert daily("2026-12-25", **MUMBAI)["year"]["vikram_samvat"] == 2083  # Pausha, same year
    # Margashirsha can run into January (after an Adhika month): still the old year.
    assert daily("2024-01-05", **MUMBAI)["year"]["vikram_samvat"] == 2080


def test_maharashtrian_vikram_year_starts_at_kartika(daily):
    # Kalnirnay 2026 (Pune/Mumbai), October page: "श्री शालिवाहन शके १९४८, पराभवनाम संवत्सर,
    # विक्रम संवत २०८२". The Vikram year turns at Kartika Shukla Pratipada (Diwali Padwa).
    year = daily("2026-10-28", **PUNE, **MAHARASHTRIAN)["year"]
    assert year["vikram_samvat"] == 2082
    assert year["vikram_year_start"] == "kartika"
    assert year["shaka_samvat"] == 1948
    assert year["shaka_samvatsara"]["name"] == "Parabhava"
    assert daily("2026-11-09", **PUNE, **MAHARASHTRIAN)["year"]["vikram_samvat"] == 2082  # Ashwin
    assert daily("2026-11-10", **PUNE, **MAHARASHTRIAN)["year"]["vikram_samvat"] == 2083  # Padwa
    # From January to Gudi Padwa both reckonings agree; Shaka still turns at Gudi Padwa.
    march = daily("2026-03-20", **PUNE, **MAHARASHTRIAN)["year"]
    assert (march["vikram_samvat"], march["shaka_samvat"]) == (2082, 1948)
    # North Indian style, same day and place: Chaitradi year.
    assert daily("2026-10-28", **PUNE)["year"]["vikram_samvat"] == 2083


def test_ritu_follows_the_lunar_month(daily):
    assert daily("2026-04-10", **MUMBAI)["year"]["ritu"] == "Vasanta"  # Chaitra
    assert daily("2026-01-15", **MUMBAI)["year"]["ritu"] == "Hemanta"  # Pausha


def test_sun_and_moon_rashi_and_nakshatra_match_drik(daily):
    # Drik: Toronto 2026-10-17 Surya Nakshatra Chitra, Moon sign Dhanu;
    # Mumbai 2026-11-08 Sun sign Tula, Surya Nakshatra Vishakha, Moon sign Tula.
    toronto = daily("2026-10-17", **TORONTO)
    assert toronto["sun_nakshatra"]["at_sunrise"]["name"] == "Chitra"
    assert toronto["moon_sign"]["at_sunrise"]["name"] == "Dhanu"
    mumbai = daily("2026-11-08", **MUMBAI)
    assert mumbai["sun_sign"]["at_sunrise"]["name"] == "Tula"
    assert mumbai["sun_nakshatra"]["at_sunrise"]["name"] == "Vishakha"
    assert mumbai["moon_sign"]["at_sunrise"]["name"] == "Tula"
