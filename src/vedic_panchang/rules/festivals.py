"""Festival rule sets, loaded from ``data/festivals/<set>.toml``.

Lunar months in rule files are always given in the Amanta system (new moon to new moon),
which is unambiguous across traditions; responses display them in the profile's month
system. Tithis are numbered 1-30 (1-15 Shukla, 16-30 Krishna; 15 = Purnima, 30 = Amavasya).
"""

import tomllib
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from functools import cache
from importlib import resources

MONTH_IDS = (
    "chaitra", "vaishakha", "jyeshtha", "ashadha", "shravana", "bhadrapada",
    "ashwin", "kartika", "margashirsha", "pausha", "magha", "phalguna",
)  # fmt: skip
SIGN_IDS = (
    "mesha", "vrishabha", "mithuna", "karka", "simha", "kanya",
    "tula", "vrishchika", "dhanu", "makara", "kumbha", "meena",
)  # fmt: skip


class Kala(StrEnum):
    """Part of the day during which the Tithi must prevail for the observance."""

    SUNRISE = "sunrise"  # instant of sunrise
    SUNSET = "sunset"  # instant of sunset
    ARUNODAYA = "arunodaya"  # 96 minutes (4 ghatis) before sunrise
    PURVAHNA = "purvahna"  # first half of daytime
    MADHYAHNA = "madhyahna"  # 3rd of 5 daytime parts
    APARAHNA = "aparahna"  # 4th of 5 daytime parts
    SAYANKALA = "sayankala"  # 5th of 5 daytime parts (until sunset)
    PRADOSH = "pradosh"  # first fifth of the night after sunset
    NISHITA = "nishita"  # 8th of 15 night muhurtas (around midnight)
    MOONRISE = "moonrise"  # instant of moonrise within the Panchang day


class TieBreak(StrEnum):
    """Which day to choose when the Tithi prevails during the kala on two days."""

    FIRST = "first"
    SECOND = "second"
    MAX_COVERAGE = "max_coverage"  # the day on which the Tithi covers more of the kala
    # The first day on which the Tithi covers the whole kala; otherwise the day it prevails at
    # sunrise (Drik Sita Navami Toronto 2027-05-14: Navami began 1 min into Madhyahna on the 13th).
    FULL = "full"


class AdhikaPolicy(StrEnum):
    NEVER = "never"  # only in regular (Nija) months — yearly festivals
    ONLY = "only"  # only in Adhika months (e.g. Padmini Ekadashi)
    BOTH = "both"  # every month — monthly observances
    FIRST = "first"  # the Adhika month when there is one, else the Nija month (Ganga Dussehra)


class Category(StrEnum):
    MAJOR = "major"
    OBSERVANCE = "observance"


_DEFAULT_TIE = {Kala.SUNRISE: TieBreak.FIRST, Kala.MOONRISE: TieBreak.FIRST}


@dataclass(frozen=True)
class LunarRule:
    id: str
    name: str  # may contain {masa}: the month name in the profile's month system
    short_name: str  # label for tight spaces (calendar cells)
    category: Category
    tithi: int
    amanta_month: int | None  # 0-11, None = every month
    adhika: AdhikaPolicy
    kala: Kala
    tie: TieBreak
    skip_amanta_months: frozenset[int]
    # Exclude time under Bhadra (Vishti karana) from the kala, e.g. Raksha Bandhan.
    avoid_bhadra: bool = False
    # Puja / observance times to report, by muhurta recipe (domain/festivals/muhurta.py).
    puja: tuple[str, ...] = ()
    # One of the Sade Teen (3 1/2) Muhurat days: "full" or "half"; None otherwise.
    sade_teen_muhurat: str | None = None
    # Kept on the Smarta Ekadashi fast day (the fast moves a day earlier when Dwadashi ends
    # before the parana sunrise). True for rules with an Ekadashi parana, and Bhishma Panchak.
    ekadashi_day: bool = False


@dataclass(frozen=True)
class SolarRule:
    """Sankranti: the Sun entering a sidereal sign. Observed the next day if after sunset."""

    id: str
    name: str  # may contain {sign}
    short_name: str
    category: Category
    sign: int | None  # 0-11, None = every sign
    puja: tuple[str, ...] = ()
    # Days after (or, if negative, before) the Sankranti's day, e.g. Lohri = -1 (eve of Makar).
    day_offset: int = 0
    # False for a festival kept alongside the Sankranti (Baisakhi with Mesha Sankranti); the
    # generic "{sign} Sankranti" entry is then still listed.
    replaces_sankranti: bool = True
    # "sunset": a Sankranti after sunset is kept the next day (default). "civil": kept on the
    # local calendar date of the Sun's ingress, as Drik does for Vishwakarma Puja and Baisakhi.
    day_rule: str = "sunset"


@dataclass(frozen=True)
class FixedRule:
    """A fixed Gregorian date, e.g. a date set by a government (Shiv Jayanti, 19 February)."""

    id: str
    name: str
    short_name: str
    category: Category
    month: int  # 1-12
    day: int  # 1-31


@dataclass(frozen=True)
class FestivalSet:
    id: str
    rule_version: str
    lunar: tuple[LunarRule, ...]
    solar: tuple[SolarRule, ...]
    fixed: tuple[FixedRule, ...] = ()

    @property
    def ids(self) -> set[str]:
        return {r.id for r in self.lunar + self.solar + self.fixed}


def _month(value: str) -> int | None:
    return None if value == "any" else MONTH_IDS.index(value)


def _lunar(raw: dict) -> LunarRule:
    tithi = int(raw["tithi"])
    if not 1 <= tithi <= 30:
        raise ValueError(f"{raw['id']}: tithi must be 1-30")
    kala = Kala(raw["kala"])
    month = _month(raw["amanta_month"])
    default_adhika = AdhikaPolicy.BOTH if month is None else AdhikaPolicy.NEVER
    return LunarRule(
        id=raw["id"],
        name=raw["name"],
        short_name=raw.get("short_name", raw["name"]),
        category=Category(raw.get("category", "observance")),
        tithi=tithi,
        amanta_month=month,
        adhika=AdhikaPolicy(raw.get("adhika", default_adhika)),
        kala=kala,
        tie=TieBreak(raw.get("tie", _DEFAULT_TIE.get(kala, TieBreak.MAX_COVERAGE))),
        skip_amanta_months=frozenset(MONTH_IDS.index(m) for m in raw.get("skip_months", [])),
        avoid_bhadra=bool(raw.get("avoid_bhadra", False)),
        puja=tuple(raw.get("puja", ())),
        sade_teen_muhurat=_sade_teen(raw),
        ekadashi_day=bool(raw.get("ekadashi_day", "parana" in raw.get("puja", ()))),
    )


def _sade_teen(raw: dict) -> str | None:
    value = raw.get("sade_teen_muhurat")
    if value not in (None, "full", "half"):
        raise ValueError(f"{raw['id']}: sade_teen_muhurat must be 'full' or 'half'")
    return value


def _solar(raw: dict) -> SolarRule:
    sign = raw.get("sign", "any")
    return SolarRule(
        id=raw["id"],
        name=raw["name"],
        short_name=raw.get("short_name", raw["name"]),
        category=Category(raw.get("category", "observance")),
        sign=None if sign == "any" else SIGN_IDS.index(sign),
        puja=tuple(raw.get("puja", ())),
        day_offset=int(raw.get("day_offset", 0)),
        replaces_sankranti=bool(raw.get("replaces_sankranti", True)),
        day_rule=_day_rule(raw),
    )


def _day_rule(raw: dict) -> str:
    value = raw.get("day_rule", "sunset")
    if value not in ("sunset", "civil"):
        raise ValueError(f"{raw['id']}: day_rule must be 'sunset' or 'civil'")
    return value


def _fixed(raw: dict) -> FixedRule:
    month, day = int(raw["month"]), int(raw["day"])
    date(2024, month, day)  # raises ValueError for an impossible date (2024 allows 29 February)
    return FixedRule(
        id=raw["id"],
        name=raw["name"],
        short_name=raw.get("short_name", raw["name"]),
        category=Category(raw.get("category", "observance")),
        month=month,
        day=day,
    )


@cache
def load_festival_set(set_id: str) -> FestivalSet:
    path = resources.files("vedic_panchang.rules").joinpath(f"data/festivals/{set_id}.toml")
    raw = tomllib.loads(path.read_text())
    festival_set = FestivalSet(
        id=set_id,
        rule_version=raw["rule_version"],
        lunar=tuple(_lunar(r) for r in raw.get("lunar", [])),
        solar=tuple(_solar(r) for r in raw.get("solar", [])),
        fixed=tuple(_fixed(r) for r in raw.get("fixed", [])),
    )
    ids = [r.id for r in festival_set.lunar + festival_set.solar + festival_set.fixed]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{set_id}: duplicate festival ids")
    return festival_set
