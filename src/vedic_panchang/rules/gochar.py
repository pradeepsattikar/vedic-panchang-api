"""Load Gochara (transit-from-Moon-sign) rules from ``data/gochar/<set>.toml``."""

import tomllib
from dataclasses import dataclass
from functools import cache
from importlib import resources

GRAHA_IDS = ("surya", "chandra", "mangal", "budha", "guru", "shukra", "shani", "rahu", "ketu")
HIGHLIGHT_KINDS = ("shani_period", "ingress", "station", "slow", "fast", "moon")


@dataclass(frozen=True)
class ShaniPeriod:
    id: str
    house: int
    name: str


@dataclass(frozen=True)
class GocharRules:
    rule_set: str
    rule_version: str
    source: str
    review_status: str
    # graha id -> {favourable house: vedha house}
    favourable: dict[str, dict[int, int]]
    exempt_pairs: frozenset[frozenset[str]]
    nodes_cause_vedha: bool
    shani_periods: tuple[ShaniPeriod, ...]
    combustion: dict[str, float]  # graha id (or "<id>_retrograde") -> orb in degrees
    highlight_order: tuple[str, ...]

    def is_exempt(self, graha: str, obstructer: str) -> bool:
        return frozenset((graha, obstructer)) in self.exempt_pairs

    def causes_vedha(self, graha: str) -> bool:
        return self.nodes_cause_vedha or graha not in ("rahu", "ketu")


def _house(rule_set: str, value) -> int:
    house = int(value)
    if not 1 <= house <= 12:
        raise ValueError(f"{rule_set}: house {value} must be 1-12")
    return house


def _parse(rule_set: str, raw: dict) -> GocharRules:
    grahas = raw["graha"]
    if set(grahas) != set(GRAHA_IDS):
        raise ValueError(f"{rule_set}: [graha] must list exactly {GRAHA_IDS}")
    favourable = {}
    for gid in GRAHA_IDS:
        table = {_house(rule_set, k): _house(rule_set, v)
                 for k, v in grahas[gid]["favourable"].items()}  # fmt: skip
        if any(k == v for k, v in table.items()):
            raise ValueError(f"{rule_set}: {gid} has a Vedha house equal to its own house")
        favourable[gid] = table
    pairs = frozenset(frozenset(p) for p in raw["vedha"]["exempt_pairs"])
    if any(len(p) != 2 or not p <= set(GRAHA_IDS) for p in pairs):
        raise ValueError(f"{rule_set}: exempt_pairs must be pairs of graha ids")
    order = tuple(raw["highlights"]["order"])
    if sorted(order) != sorted(HIGHLIGHT_KINDS):
        raise ValueError(f"{rule_set}: highlights.order must list each of {HIGHLIGHT_KINDS}")
    periods = tuple(
        ShaniPeriod(p["id"], _house(rule_set, p["house"]), p["name"]) for p in raw["shani_period"]
    )
    return GocharRules(
        rule_set=rule_set,
        rule_version=raw["rule_version"],
        source=raw["source"],
        review_status=raw["review_status"],
        favourable=favourable,
        exempt_pairs=pairs,
        nodes_cause_vedha=bool(raw["vedha"]["nodes_cause_vedha"]),
        shani_periods=periods,
        combustion={k: float(v) for k, v in raw["combustion"].items()},
        highlight_order=order,
    )


@cache
def load_gochar_rules(rule_set: str = "phaladeepika") -> GocharRules:
    text = resources.files("vedic_panchang.rules").joinpath(f"data/gochar/{rule_set}.toml")
    return _parse(rule_set, tomllib.loads(text.read_text(encoding="utf-8")))
