"""Calculation profiles: North Indian (Purnimanta, default) and Maharashtrian (Amanta).

The Maharashtrian profile inherits everything from the North Indian one except the month system
(founder, 2026-10-26). Amanta months end at Amavasya, so in Krishna Paksha the month is named one
earlier than in the North: 2026-10-28 is Kartika Krishna in the North, Ashwin Krishna in Pune.
"""

import pytest

from vedic_panchang.rules.profiles import _resolve, load_profiles

PUNE = "1259229"
MH = "maharashtrian-smarta"


def test_both_profiles_listed_and_north_indian_is_default(client):
    meta = client.get("/v1/meta").json()
    assert meta["default_profile"] == "north-indian-smarta"
    profiles = {p["id"]: p for p in meta["profiles"]}
    assert profiles["north-indian-smarta"]["month_system"] == "purnimanta"
    assert profiles[MH]["month_system"] == "amanta"
    assert profiles[MH]["name"] == "Maharashtrian (Amanta), Smarta observance"


def test_maharashtrian_inherits_everything_but_the_month_system():
    registry = load_profiles()
    north, mh = registry.get(None), registry.get(MH)
    assert mh.ayanamsha == north.ayanamsha
    assert mh.day_anchor == north.day_anchor
    assert mh.day_periods == north.day_periods
    assert mh.abhijit_excluded_weekdays == north.abhijit_excluded_weekdays
    assert mh.lunar_node == north.lunar_node
    assert mh.shubh_set == north.shubh_set
    assert mh.muhurta_set == north.muhurta_set
    assert (mh.month_system, north.month_system) == ("amanta", "purnimanta")
    assert mh.rule_version  # has its own version, so caches and responses are labelled


def test_daily_values_are_identical_apart_from_the_profile_label(daily):
    north = daily("2026-10-28", city_id=PUNE)
    mh = daily("2026-10-28", city_id=PUNE, profile=MH)
    assert mh["request"]["profile"] == MH
    assert mh["profile"]["id"] == MH
    # Both month systems are always returned; the profile says which one to display.
    assert mh["masa"] == north["masa"]
    assert mh["masa"]["amanta"]["name"] == "Ashwin"
    assert mh["masa"]["purnimanta"]["name"] == "Kartika"
    for key in ("tithi", "nakshatra", "yoga", "karana", "sun", "moon", "timings", "grahas", "year"):
        assert mh[key] == north[key], key


def test_festival_names_use_the_profiles_month_system(client):
    def amavasya(profile: str | None) -> tuple[str, str]:
        params = {"year": 2026, "city_id": PUNE} | ({"profile": profile} if profile else {})
        body = client.get("/v1/festivals", params=params).json()
        hit = next(
            f
            for f in body["festivals"]
            if f["date"] == "2026-11-09" and f["festival_id"] == "amavasya"
        )
        return hit["name"], hit["date"]

    assert amavasya(None) == ("Kartika Amavasya", "2026-11-09")
    assert amavasya(MH) == ("Ashwin Amavasya", "2026-11-09")


def test_festival_dates_match_between_profiles(client):
    def dates(profile: str | None) -> list[tuple[str, str]]:
        params = {"year": 2026, "city_id": PUNE} | ({"profile": profile} if profile else {})
        body = client.get("/v1/festivals", params=params).json()
        return [(f["occurrence_id"], f["date"]) for f in body["festivals"]]

    assert dates(MH) == dates(None)


def test_month_and_muhurta_accept_the_profile(client):
    month = client.get(
        "/v1/panchang/month", params={"year": 2026, "month": 11, "city_id": PUNE, "profile": MH}
    )
    assert month.status_code == 200, month.text
    assert month.json()["profile"]["id"] == MH
    muhurta = client.get(
        "/v1/muhurta",
        params={
            "purpose": "vivah",
            "date": "2026-11-20",
            "days": 30,
            "city_id": PUNE,
            "profile": MH,
        },
    )
    assert muhurta.status_code == 200, muhurta.text
    assert muhurta.json()["profile"]["id"] == MH


def test_unknown_profile_is_a_structured_error(client):
    response = client.get(
        "/v1/panchang/daily", params={"date": "2026-10-28", "city_id": PUNE, "profile": "nope"}
    )
    assert response.status_code in (400, 404, 422)
    assert MH in response.text  # the error lists the available profiles


def test_inheritance_merges_nested_tables_and_rejects_loops():
    raw = {
        "base": {"name": "Base", "day_periods": {"rahu_kalam": {"monday": 2, "tuesday": 7}}},
        "child": {
            "inherits": "base",
            "name": "Child",
            "day_periods": {"rahu_kalam": {"monday": 3}},
        },
    }
    child = _resolve("child", raw)
    assert child["name"] == "Child"
    assert child["day_periods"]["rahu_kalam"] == {"monday": 3, "tuesday": 7}
    assert "inherits" not in child
    with pytest.raises(ValueError, match="loop"):
        _resolve("a", {"a": {"inherits": "b"}, "b": {"inherits": "a"}})
    with pytest.raises(ValueError, match="unknown"):
        _resolve("a", {"a": {"inherits": "missing"}})
