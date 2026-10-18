"""Load general muhurta rules from ``data/muhurta/<set>.toml``."""

import tomllib
from dataclasses import dataclass
from functools import cache
from importlib import resources

from vedic_panchang.rules.festivals import MONTH_IDS, SIGN_IDS
from vedic_panchang.rules.profiles import WEEKDAYS


class UnknownPurposeError(LookupError):
    def __init__(self, purpose_id: str, available: list[str]):
        super().__init__(f"Unknown muhurta purpose '{purpose_id}'")
        self.available = available


@dataclass(frozen=True)
class Purpose:
    id: str
    name: str
    description: str
    nakshatras: frozenset[str]  # Nakshatra ids, e.g. "uttara-phalguni"
    tithis: frozenset[int]  # 1-30
    weekdays_excluded: frozenset[int]  # Python weekday, Monday = 0
    lunar_months: frozenset[int] | None  # Amanta month index 0-11; None = any
    solar_months_excluded: frozenset[int]  # sidereal sign index 0-11
    yogas_excluded: frozenset[str]
    avoid_bhadra: bool
    avoid_gandanta: bool
    avoid_chaturmas: bool
    asta: tuple[str, ...]  # "jupiter", "venus"


@dataclass(frozen=True)
class AstaLimits:
    jupiter: float
    venus: float
    venus_near_inferior_conjunction: float


@dataclass(frozen=True)
class MuhurtaRules:
    id: str
    rule_version: str
    min_minutes: int
    asta: AstaLimits
    purposes: tuple[Purpose, ...]

    def purpose(self, purpose_id: str) -> Purpose:
        for purpose in self.purposes:
            if purpose.id == purpose_id:
                return purpose
        raise UnknownPurposeError(purpose_id, [p.id for p in self.purposes])


def _purpose(raw: dict) -> Purpose:
    months = raw["lunar_months"]
    tithis = frozenset(int(t) for t in raw["tithis"])
    if not all(1 <= t <= 30 for t in tithis):
        raise ValueError(f"{raw['id']}: tithis must be 1-30")
    return Purpose(
        id=raw["id"],
        name=raw["name"],
        description=raw["description"],
        nakshatras=frozenset(raw["nakshatras"]),
        tithis=tithis,
        weekdays_excluded=frozenset(WEEKDAYS.index(d) for d in raw["weekdays_excluded"]),
        lunar_months=None if months == "any" else frozenset(MONTH_IDS.index(m) for m in months),
        solar_months_excluded=frozenset(SIGN_IDS.index(s) for s in raw["solar_months_excluded"]),
        yogas_excluded=frozenset(raw["yogas_excluded"]),
        avoid_bhadra=bool(raw["avoid_bhadra"]),
        avoid_gandanta=bool(raw["avoid_gandanta"]),
        avoid_chaturmas=bool(raw["avoid_chaturmas"]),
        asta=tuple(raw["asta"]),
    )


@cache
def load_muhurta_rules(set_id: str = "north-indian-smarta") -> MuhurtaRules:
    text = resources.files("vedic_panchang.rules").joinpath(f"data/muhurta/{set_id}.toml")
    raw = tomllib.loads(text.read_text(encoding="utf-8"))
    asta = raw["asta"]
    return MuhurtaRules(
        id=set_id,
        rule_version=raw["rule_version"],
        min_minutes=int(raw["min_minutes"]),
        asta=AstaLimits(
            jupiter=float(asta["jupiter"]),
            venus=float(asta["venus"]),
            venus_near_inferior_conjunction=float(asta["venus_near_inferior_conjunction"]),
        ),
        purposes=tuple(_purpose(p) for p in raw["purpose"]),
    )
