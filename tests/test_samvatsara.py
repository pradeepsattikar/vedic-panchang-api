"""Samvatsara (60-year cycle) vs Drik Panchang, New Delhi (checked 2026-10-27).

Drik shows the Vikram year name (North Indian, Jupiter cycle), the Shaka year name (fixed cycle)
and the moment the Jupiter samvatsara changes. Vikram 2085 shows the skip (kshaya) of Durmati.
"""

from datetime import UTC, datetime, timedelta

import pytest

from vedic_panchang.astronomy.julian import from_jd, to_jd
from vedic_panchang.domain.panchang import names
from vedic_panchang.domain.panchang.samvatsara import (
    JOVIAN_YEAR_DAYS,
    jovian_index,
    shaka_samvatsara,
)

NEW_DELHI = "1261481"
IST = timedelta(hours=5, minutes=30)

# 1 May of each year (after the new year): Vikram year and name, Shaka year and name.
DRIK_YEARS = [
    ("2022-05-01", 2079, "Rakshasa", 1944, "Shubhakrit"),
    ("2024-05-01", 2081, "Pingala", 1946, "Krodhi"),
    ("2025-05-01", 2082, "Kalayukta", 1947, "Vishvavasu"),
    ("2026-05-01", 2083, "Siddharthi", 1948, "Parabhava"),
    ("2026-10-27", 2083, "Siddharthi", 1948, "Parabhava"),
    ("2027-05-01", 2084, "Raudra", 1949, "Plavanga"),
    ("2028-05-01", 2085, "Dundubhi", 1950, "Kilaka"),  # Durmati skipped
    ("2029-05-01", 2086, "Rudhirodgari", 1951, "Saumya"),
    ("2030-05-01", 2087, "Raktaksha", 1952, "Sadharana"),
    ("2031-05-01", 2088, "Krodhana", 1953, "Virodhakrit"),
]

# When the Jupiter samvatsara ends (IST), from Drik's "<name> upto <time>".
DRIK_CHANGES = [
    ("Rakshasa", "2022-05-08 12:39"),
    ("Pingala", "2024-04-29 14:14"),
    ("Kalayukta", "2025-04-25 15:07"),
    ("Siddharthi", "2026-04-21 15:53"),
    ("Raudra", "2027-04-17 16:25"),
    ("Durmati", "2028-04-12 17:04"),
    ("Dundubhi", "2029-04-08 17:17"),
    ("Rudhirodgari", "2030-04-04 18:04"),
    ("Raktaksha", "2031-03-31 18:45"),
    ("Krodhana", "2032-03-26 19:37"),
]


@pytest.mark.parametrize(("day", "vikram", "vikram_name", "shaka", "shaka_name"), DRIK_YEARS)
def test_year_names_match_drik(daily, day, vikram, vikram_name, shaka, shaka_name):
    year = daily(day, city_id=NEW_DELHI)["year"]
    assert (year["vikram_samvat"], year["vikram_samvatsara"]["name"]) == (vikram, vikram_name)
    assert (year["shaka_samvat"], year["shaka_samvatsara"]["name"]) == (shaka, shaka_name)


@pytest.mark.parametrize(("name", "ends_ist"), DRIK_CHANGES)
def test_jupiter_samvatsara_changes_within_21_minutes_of_drik(name, ends_ist):
    end = to_jd(datetime.fromisoformat(ends_ist).replace(tzinfo=UTC) - IST)
    before, after = jovian_index(end - 21 / 1440), jovian_index(end + 21 / 1440)
    assert names.SAMVATSARAS[before] == name
    assert after == (before + 1) % 60


def test_the_year_names_are_the_same_in_every_profile(daily):
    north = daily("2026-10-27", city_id=NEW_DELHI)["year"]
    mh = daily("2026-10-27", city_id=NEW_DELHI, profile="maharashtrian-smarta")["year"]
    for key in ("vikram_samvatsara", "shaka_samvatsara", "shaka_samvat"):
        assert north[key] == mh[key], key


def test_names_change_with_the_samvat_year(daily):
    # Chaitra Shukla Pratipada 2025 was 30 March (New Delhi).
    before = daily("2025-03-28", city_id=NEW_DELHI)["year"]
    after = daily("2025-04-02", city_id=NEW_DELHI)["year"]
    assert (before["vikram_samvatsara"]["name"], before["shaka_samvatsara"]["name"]) == (
        "Pingala",
        "Krodhi",
    )
    assert (after["vikram_samvatsara"]["name"], after["shaka_samvatsara"]["name"]) == (
        "Kalayukta",
        "Vishvavasu",
    )


def test_cycle_facts():
    assert len(names.SAMVATSARAS) == 60
    assert len(set(names.SAMVATSARAS)) == 60
    assert shaka_samvatsara(1948).number == 40
    assert shaka_samvatsara(1948).id == "parabhava"
    assert shaka_samvatsara(1948 + 60) == shaka_samvatsara(1948)
    assert 361.02 < JOVIAN_YEAR_DAYS < 361.03
    assert from_jd(to_jd(datetime(2026, 1, 1, tzinfo=UTC)), UTC).year == 2026
