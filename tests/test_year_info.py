"""Samvat, Ritu, Ayana and Sun/Moon Rashi (preview additions), against Drik Panchang.

Drik, Toronto 2026-10-17: Vikram Samvat 2083, Shaka Samvat 1948, Ritu Sharad, Ayana
Dakshinayana, Sun sign Kanya until 10:27 AM then Tula, Moon sign Dhanu.
"""

from tests.conftest import minutes_apart

TORONTO = {"city_id": "6167865"}
MUMBAI = {"city_id": "1275339"}


def test_matches_drik_toronto(daily):
    body = daily("2026-10-17", **TORONTO)
    assert body["year"] == {
        "vikram_samvat": 2083,
        "shaka_samvat": 1948,
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


def test_ritu_follows_the_lunar_month(daily):
    assert daily("2026-04-10", **MUMBAI)["year"]["ritu"] == "Vasanta"  # Chaitra
    assert daily("2026-01-15", **MUMBAI)["year"]["ritu"] == "Hemanta"  # Pausha
