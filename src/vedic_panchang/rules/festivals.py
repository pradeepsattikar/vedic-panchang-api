"""Festival rule sets, loaded from ``data/festivals/<set>.toml``.

Lunar months in rule files are always given in the Amanta system (new moon to new moon),
which is unambiguous across traditions; responses display them in the profile's month
system. Tithis are numbered 1-30 (1-15 Shukla, 16-30 Krishna; 15 = Purnima, 30 = Amavasya).
"""

import tomllib
from dataclasses import dataclass
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
    PRADOSH = "pradosh"  # first fifth of the night after sunset
    NISHITA = "nishita"  # 8th of 15 night muhurtas (around midnight)
    MOONRISE = "moonrise"  # instant of moonrise within the Panchang day


class TieBreak(StrEnum):
    """Which day to choose when the Tithi prevails during the kala on two days."""

    FIRST = "first"
    SECOND = "second"
    MAX_COVERAGE = "max_coverage"  # the day on which the Tithi covers more of the kala


class AdhikaPolicy(StrEnum):
    NEVER = "never"  # only in regular (Nija) months — yearly festivals
    ONLY = "only"  # only in Adhika months (e.g. Padmini Ekadashi)
    BOTH = "both"  # every month — monthly observances


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


@dataclass(frozen=True)
class SolarRule:
    """Sankranti: the Sun entering a sidereal sign. Observed the next day if after sunset."""

    id: str
    name: str  # may contain {sign}
    short_name: str
    category: Category
    sign: int | None  # 0-11, None = every sign


@dataclass(frozen=True)
class FestivalSet:
    id: str
    rule_version: str
    lunar: tuple[LunarRule, ...]
    solar: tuple[SolarRule, ...]


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
    )


def _solar(raw: dict) -> SolarRule:
    sign = raw.get("sign", "any")
    return SolarRule(
        id=raw["id"],
        name=raw["name"],
        short_name=raw.get("short_name", raw["name"]),
        category=Category(raw.get("category", "observance")),
        sign=None if sign == "any" else SIGN_IDS.index(sign),
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
    )
    ids = [r.id for r in festival_set.lunar + festival_set.solar]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{set_id}: duplicate festival ids")
    return festival_set
