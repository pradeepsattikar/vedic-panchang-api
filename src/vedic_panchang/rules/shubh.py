"""Load Shubh Yoga rules (auspicious weekday/Nakshatra/Tithi combinations) from
``data/shubh/<set>.toml``."""

import tomllib
from dataclasses import dataclass
from functools import cache
from importlib import resources

from vedic_panchang.rules.profiles import WEEKDAYS

_NAKSHATRA_IDS = frozenset((
    "ashwini", "bharani", "krittika", "rohini", "mrigashira", "ardra", "punarvasu", "pushya",
    "ashlesha", "magha", "purva-phalguni", "uttara-phalguni", "hasta", "chitra", "swati",
    "vishakha", "anuradha", "jyeshtha", "mula", "purva-ashadha", "uttara-ashadha", "shravana",
    "dhanishtha", "shatabhisha", "purva-bhadrapada", "uttara-bhadrapada", "revati",
))  # fmt: skip


@dataclass(frozen=True)
class ShubhYogaRule:
    id: str
    name: str
    how: str  # how the combination is formed, in plain English
    note: str | None
    special: bool  # rare and widely observed: starred on the Calendar
    # weekday (Python, Monday = 0) -> Nakshatra ids allowed on it; None = any weekday/Nakshatra
    weekday_nakshatras: dict[int, frozenset[str]] | None
    tithis: frozenset[int] | None  # 1-30; None = any
    sun_moon_counts: frozenset[int] | None  # Ravi Yoga: Moon's Nakshatra counted from the Sun's

    def matches(self, weekday: int, nakshatra: str, tithi: int, sun_nakshatra: int,
                moon_nakshatra: int) -> bool:  # fmt: skip
        table = self.weekday_nakshatras
        if table is not None and nakshatra not in table.get(weekday, frozenset()):
            return False
        if self.tithis is not None and tithi not in self.tithis:
            return False
        if self.sun_moon_counts is not None:
            count = (moon_nakshatra - sun_nakshatra) % 27 + 1
            if count not in self.sun_moon_counts:
                return False
        return True


@dataclass(frozen=True)
class ShubhRules:
    rule_version: str
    yogas: tuple[ShubhYogaRule, ...]


def _nakshatras(rule_id: str, values: list[str]) -> frozenset[str]:
    unknown = set(values) - _NAKSHATRA_IDS
    if unknown:
        raise ValueError(f"{rule_id}: unknown Nakshatra ids {sorted(unknown)}")
    return frozenset(values)


def _parse(raw: dict) -> ShubhYogaRule:
    rid = raw["id"]
    if "weekday_nakshatras" in raw:
        table = {WEEKDAYS.index(day): _nakshatras(rid, naks)
                 for day, naks in raw["weekday_nakshatras"].items()}  # fmt: skip
    elif "weekdays" in raw:
        naks = _nakshatras(rid, raw["nakshatras"])
        table = {WEEKDAYS.index(day): naks for day in raw["weekdays"]}
    else:
        table = None
    tithis = frozenset(raw["tithis"]) if "tithis" in raw else None
    if tithis and not all(1 <= t <= 30 for t in tithis):
        raise ValueError(f"{rid}: tithis must be 1-30")
    counts = frozenset(raw["sun_moon_counts"]) if "sun_moon_counts" in raw else None
    return ShubhYogaRule(
        id=rid,
        name=raw["name"],
        how=raw["how"],
        note=raw.get("note"),
        special=bool(raw.get("special", False)),
        weekday_nakshatras=table,
        tithis=tithis,
        sun_moon_counts=counts,
    )


@cache
def load_shubh_rules(rule_set: str = "north-indian-smarta") -> ShubhRules:
    text = resources.files("vedic_panchang.rules").joinpath(f"data/shubh/{rule_set}.toml")
    raw = tomllib.loads(text.read_text(encoding="utf-8"))
    return ShubhRules(rule_version=raw["rule_version"],
                      yogas=tuple(_parse(y) for y in raw["yoga"]))  # fmt: skip
