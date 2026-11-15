"""Gochara (transits from the natal Moon sign): calculation, Phaladeepika judgment, endpoint.

Drik Panchang references (New Delhi pages, read 2026-11-15). Drik's sign changes come later
than ours by the same Lahiri-variant gap as its Sankrantis (see CLAUDE.md, "Lahiri variant");
for slow planets that small angle is many minutes (Jupiter ~35-50 min), so the tolerances
below are wide on purpose. Stations are when a planet stands still, so their instant is
inherently imprecise (Drik vs ours within ~1 h).
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from vedic_panchang.astronomy.ephemeris import Ayanamsha
from vedic_panchang.domain.gochar.engine import house_from_moon, judge, weekly_gochar
from vedic_panchang.rules.gochar import GRAHA_IDS, load_gochar_rules

IST = ZoneInfo("Asia/Kolkata")
TORONTO = ZoneInfo("America/Toronto")
RULES = load_gochar_rules()
MESHA, SIMHA, DHANU, MAKARA, KUMBHA, MEENA = 0, 4, 8, 9, 10, 11


def week(first: date, days: int = 7, tz: ZoneInfo = TORONTO):
    return weekly_gochar(first, days, tz, Ayanamsha.LAHIRI, "mean", RULES)


@pytest.fixture(scope="module")
def nov16():
    return week(date(2026, 11, 16))


@pytest.fixture(scope="module")
def year2026():
    return week(date(2026, 1, 1), 365, IST)


# ── step 2: house from the Moon sign ─────────────────────────────


@pytest.mark.parametrize(
    ("transit", "moon", "house"),
    [
        (SIMHA, MESHA, 5),
        (MEENA, MESHA, 12),
        (MESHA, MEENA, 2),
        (MESHA, MESHA, 1),
        (MEENA, KUMBHA, 2),
    ],
)
def test_house_from_moon(transit, moon, house):
    assert house_from_moon(transit, moon) == house


# ── rule data ────────────────────────────────────────────────────

PHALADEEPIKA_FAVOURABLE = {
    "surya": {3, 6, 10, 11},
    "chandra": {1, 3, 6, 7, 10, 11},
    "mangal": {3, 6, 11},
    "budha": {2, 4, 6, 8, 10, 11},
    "guru": {2, 5, 7, 9, 11},
    "shukra": {1, 2, 3, 4, 5, 8, 9, 11, 12},
    "shani": {3, 6, 11},
    "rahu": {3, 6, 11},
    "ketu": {3, 6, 11},
}


def test_rule_file_has_the_favourable_houses_for_every_graha():
    assert set(RULES.favourable) == set(GRAHA_IDS)
    for graha, houses in PHALADEEPIKA_FAVOURABLE.items():
        assert set(RULES.favourable[graha]) == houses, graha


def test_rule_file_is_marked_as_unreviewed_draft():
    # Remove this test when a Jyotishi has checked the tables against the text.
    assert RULES.review_status == "pending"
    assert RULES.rule_version.endswith("-draft")


# ── step 3: judgment and Vedha ───────────────────────────────────


def signs(**placed: int) -> dict[str, int]:
    """Every graha parked in a sign that is house 7 from Mesha (Tula) unless placed."""
    return {g: placed.get(g, 6) for g in GRAHA_IDS}


def test_favourable_house_without_vedha():
    j = judge(RULES, "guru", signs(guru=SIMHA), MESHA)  # 5th, Vedha house 4 empty
    assert (j.house, j.status, j.vedha_house, j.vedha_by) == (5, "favourable", 4, ())


def test_vedha_obstructs_a_favourable_house():
    j = judge(RULES, "guru", signs(guru=SIMHA, mangal=3), MESHA)  # Mars in Karka = 4th
    assert (j.status, j.vedha_by) == ("obstructed", ("mangal",))


def test_unfavourable_house_has_no_vedha():
    j = judge(RULES, "mangal", signs(mangal=SIMHA), MESHA)  # Mars 5th
    assert (j.status, j.vedha_house) == ("unfavourable", None)


@pytest.mark.parametrize(
    ("graha", "house_sign", "other", "vedha_sign"),
    [
        ("surya", 2, "shani", 8),  # Sun 3rd, Saturn in the 9th: exempt (father and son)
        ("shani", 2, "surya", 8),  # and the other way round
        ("chandra", 2, "budha", 8),  # Moon 3rd, Mercury 9th: exempt
    ],
)
def test_exempt_pairs_do_not_obstruct(graha, house_sign, other, vedha_sign):
    j = judge(RULES, graha, signs(**{graha: house_sign, other: vedha_sign}), MESHA)
    assert j.status == "favourable"


# ── worked example: week of 16 Nov 2026 (Toronto), Moon sign Mesha ──


def test_week_window_is_local_midnight(nov16):
    assert nov16.start == datetime(2026, 11, 16, tzinfo=TORONTO)
    assert nov16.end == datetime(2026, 11, 23, tzinfo=TORONTO)


def test_sign_spans_cover_the_window_without_gaps(nov16):
    for spans in nov16.sign_spans.values():
        assert nov16.at(spans[0].start_jd) == nov16.start
        assert nov16.at(spans[-1].end_jd) == nov16.end
        for a, b in zip(spans, spans[1:], strict=False):
            assert a.end_jd == b.start_jd and a.sign != b.sign


def test_signs_this_week(nov16):
    def path(g):
        return [nov16.rashi(s.sign) for s in nov16.sign_spans[g]]

    assert path("surya") == ["Tula", "Vrishchika"]
    assert path("chandra") == ["Makara", "Kumbha", "Meena", "Mesha"]
    assert path("shukra") == ["Kanya", "Tula"]
    for g, sign in [("mangal", "Simha"), ("guru", "Simha"), ("ketu", "Simha"),
                    ("budha", "Tula"), ("shani", "Meena"), ("rahu", "Kumbha")]:  # fmt: skip
        assert path(g) == [sign]
    assert {g.graha for g in nov16.at_start if g.retrograde} == {"shani", "rahu", "ketu"}
    assert nov16.stations == () and nov16.combust == ()


def test_mesha_judgments(nov16):
    mesha = nov16.moon_signs[MESHA]
    got = {(t.graha, t.house): (t.status, t.vedha_by) for t in mesha.transits}
    assert got[("guru", 5)] == ("favourable", ())
    assert got[("chandra", 10)] == ("favourable", ())
    assert got[("chandra", 11)] == ("obstructed", ("surya",))  # Sun now in the 8th
    assert got[("chandra", 12)] == ("unfavourable", ())
    assert got[("chandra", 1)] == ("obstructed", ("mangal", "guru", "ketu"))
    assert got[("rahu", 11)] == ("obstructed", ("mangal", "guru", "ketu"))
    assert got[("mangal", 5)][0] == got[("shani", 12)][0] == "unfavourable"
    assert [f.id for f in mesha.shani_flags] == ["sade_sati_1"]


def test_mesha_highlights_follow_the_fixed_order(nov16):
    hl = [(h.kind, h.graha, h.rule_ids) for h in nov16.moon_signs[MESHA].highlights]
    assert hl == [
        ("shani_period", "shani", ("sade_sati_1",)),
        ("ingress", "surya", ("surya_h8",)),
        ("ingress", "shukra", ("shukra_h7",)),
        ("fast", "budha", ("budha_h7",)),
        ("fast", "mangal", ("mangal_h5",)),
        ("slow", "guru", ("guru_h5",)),
        ("slow", "shani", ("shani_h12",)),
        ("slow", "rahu", ("rahu_h11_vedha",)),
        ("slow", "ketu", ("ketu_h5",)),
        (
            "moon",
            "chandra",
            ("chandra_h10", "chandra_h11_vedha", "chandra_h12", "chandra_h1_vedha"),
        ),
    ]


def test_shani_periods_for_saturn_in_meena(nov16):
    flags = {m.moon_sign: [f.id for f in m.shani_flags] for m in nov16.moon_signs}
    assert flags[MESHA] == ["sade_sati_1"]
    assert flags[MEENA] == ["sade_sati_2"]
    assert flags[KUMBHA] == ["sade_sati_3"]
    assert flags[DHANU] == ["kantaka_shani"]
    assert flags[SIMHA] == ["ashtama_shani"]
    assert sum(1 for f in flags.values() if f) == 5


# ── sign changes match our verified Panchang and Drik ───────────


def test_sun_ingress_is_the_verified_sankranti(nov16):
    # Vrishchika Sankranti 2026, Toronto: 09:13 (Vedisha; Drik 09:18, Lahiri variant).
    ingress = nov16.at(nov16.sign_spans["surya"][1].start_jd)
    assert ingress.strftime("%Y-%m-%d %H:%M") == "2026-11-16 09:13"


def test_moon_ingress_matches_daily_panchang(nov16, daily):
    body = daily("2026-11-17", city_id="6167865")  # Toronto
    spans = body["moon_sign"]["spans"]
    change = next(s["start"] for s in spans if s["name"] == "Kumbha")
    ours = nov16.at(nov16.sign_spans["chandra"][1].start_jd)
    assert abs((datetime.fromisoformat(change) - ours).total_seconds()) <= 1


def _minutes(a: datetime, b: datetime) -> float:
    return abs((a - b).total_seconds()) / 60


@pytest.mark.parametrize(
    ("graha", "sign", "drik_ist", "tolerance_min"),
    [
        ("guru", "Karka", "2026-06-02 02:25", 60),
        ("guru", "Simha", "2026-10-31 12:50", 60),
    ],
)
def test_ingress_vs_drik(year2026, graha, sign, drik_ist, tolerance_min):
    span = next(s for s in year2026.sign_spans[graha] if year2026.rashi(s.sign) == sign)
    drik = datetime.strptime(drik_ist, "%Y-%m-%d %H:%M").replace(tzinfo=IST)
    assert _minutes(year2026.at(span.start_jd), drik) <= tolerance_min


@pytest.mark.parametrize(
    ("graha", "becomes", "drik_ist"),
    [
        ("shani", "retrograde", "2026-07-27 01:25"),  # Drik Madrid 26 Jul 21:55 CEST
        ("shani", "direct", "2026-12-11 05:00"),  # Drik Madrid 11 Dec 00:30 CET
        ("guru", "retrograde", "2026-12-13 06:25"),  # Drik New Delhi
    ],
)
def test_station_vs_drik(year2026, graha, becomes, drik_ist):
    station = next(s for s in year2026.stations if s.graha == graha and s.becomes == becomes
                   and year2026.at(s.jd).strftime("%Y-%m-%d")[:7] == drik_ist[:7])  # fmt: skip
    drik = datetime.strptime(drik_ist, "%Y-%m-%d %H:%M").replace(tzinfo=IST)
    assert _minutes(year2026.at(station.jd), drik) <= 90


# ── endpoint ─────────────────────────────────────────────────────


def test_endpoint(client):
    params = {"from": "2026-11-16", "tz": "America/Toronto"}
    r = client.get("/v1/gochar/weekly", params=params)
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["from_date"], body["to_date"]) == ("2026-11-16", "2026-11-22")
    assert body["review_status"] == "pending" and body["lunar_node"] == "mean"
    assert [g["id"] for g in body["grahas"]] == list(GRAHA_IDS)
    assert [m["rashi"] for m in body["moon_signs"]][:2] == ["Mesha", "Vrishabha"]
    assert len(body["moon_signs"]) == 12
    again = client.get("/v1/gochar/weekly", params=params).json()
    body.pop("generated_at"), again.pop("generated_at")
    assert body == again  # deterministic


@pytest.mark.parametrize(
    ("params", "code"),
    [({"tz": "Mars/Base"}, "invalid_location"), ({"days": 40}, "invalid_request"),
     ({"from": "2040-01-01"}, "date_out_of_range")],
)  # fmt: skip
def test_endpoint_errors(client, params, code):
    r = client.get("/v1/gochar/weekly", params=params)
    assert r.status_code == 422 and r.json()["error"]["code"] == code
