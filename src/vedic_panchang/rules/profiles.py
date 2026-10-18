"""Load calculation profiles from ``data/profiles.toml``."""

import tomllib
from dataclasses import dataclass
from functools import cache
from importlib import resources

from vedic_panchang.astronomy.ephemeris import Ayanamsha

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
DAY_PERIODS = ("rahu_kalam", "yamaganda", "gulika_kalam")


class UnknownProfileError(LookupError):
    def __init__(self, profile_id: str, available: list[str]):
        super().__init__(f"Unknown calculation profile '{profile_id}'")
        self.profile_id = profile_id
        self.available = available


@dataclass(frozen=True)
class CalculationProfile:
    id: str
    name: str
    rule_version: str
    ayanamsha: Ayanamsha
    month_system: str
    festival_convention: str
    day_anchor: str
    festival_set: str
    abhijit_excluded_weekdays: frozenset[int]
    lunar_node: str  # "mean" or "true": how Rahu and Ketu are calculated
    # period id -> 7-tuple of 1-based day parts, indexed by Python weekday (Monday = 0)
    day_periods: tuple[tuple[str, tuple[int, ...]], ...]

    def day_part(self, period_id: str, weekday: int) -> int:
        return dict(self.day_periods)[period_id][weekday]


def _parse(profile_id: str, raw: dict) -> CalculationProfile:
    if raw["day_anchor"] != "sunrise":
        raise ValueError(f"{profile_id}: only the 'sunrise' day anchor is implemented")
    periods = []
    for period_id in DAY_PERIODS:
        table = raw["day_periods"][period_id]
        parts = tuple(int(table[day]) for day in WEEKDAYS)
        if not all(1 <= p <= 8 for p in parts):
            raise ValueError(f"{profile_id}: {period_id} parts must be between 1 and 8")
        periods.append((period_id, parts))
    return CalculationProfile(
        id=profile_id,
        name=raw["name"],
        rule_version=raw["rule_version"],
        ayanamsha=Ayanamsha(raw["ayanamsha"]),
        month_system=raw["month_system"],
        festival_convention=raw["festival_convention"],
        day_anchor=raw["day_anchor"],
        festival_set=raw["festival_set"],
        abhijit_excluded_weekdays=frozenset(
            WEEKDAYS.index(day) for day in raw.get("abhijit_excluded_weekdays", [])
        ),
        lunar_node=_lunar_node(profile_id, raw.get("lunar_node", "mean")),
        day_periods=tuple(periods),
    )


def _lunar_node(profile_id: str, value: str) -> str:
    if value not in ("mean", "true"):
        raise ValueError(f"{profile_id}: lunar_node must be 'mean' or 'true'")
    return value


@dataclass(frozen=True)
class ProfileRegistry:
    default_id: str
    profiles: dict[str, CalculationProfile]

    def get(self, profile_id: str | None) -> CalculationProfile:
        key = profile_id or self.default_id
        try:
            return self.profiles[key]
        except KeyError:
            raise UnknownProfileError(key, sorted(self.profiles)) from None


@cache
def load_profiles() -> ProfileRegistry:
    text = resources.files("vedic_panchang.rules").joinpath("data/profiles.toml").read_text()
    raw = tomllib.loads(text)
    profiles = {pid: _parse(pid, body) for pid, body in raw["profiles"].items()}
    default_id = raw["default_profile"]
    if default_id not in profiles:
        raise ValueError(f"default_profile '{default_id}' is not defined")
    return ProfileRegistry(default_id=default_id, profiles=profiles)
