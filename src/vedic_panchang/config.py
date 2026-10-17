"""Runtime settings, read from environment variables (prefix ``VP_``)."""

import os
from dataclasses import dataclass, field
from datetime import date
from importlib import resources
from pathlib import Path


def _default_cities_path() -> Path:
    return Path(str(resources.files("vedic_panchang.infra").joinpath("data/cities.csv")))


@dataclass(frozen=True)
class Settings:
    # Supported date range (D03). The engine can do far more; this is what is tested.
    min_date: date = date(2020, 1, 1)
    max_date: date = date(2035, 12, 31)
    cache_size: int = 4096
    cities_path: Path = field(default_factory=_default_cities_path)
    cors_origins: tuple[str, ...] = ("*",)
    # Requests per client per minute; 0 = no limit (local development).
    rate_limit_per_minute: int = 0
    # Behind a hosting load balancer: take the client address from X-Forwarded-For.
    trust_proxy: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.environ
        defaults = cls()
        return cls(
            min_date=date.fromisoformat(env.get("VP_MIN_DATE", defaults.min_date.isoformat())),
            max_date=date.fromisoformat(env.get("VP_MAX_DATE", defaults.max_date.isoformat())),
            cache_size=int(env.get("VP_CACHE_SIZE", defaults.cache_size)),
            cities_path=Path(env.get("VP_CITIES_PATH", defaults.cities_path)),
            cors_origins=tuple(
                o.strip() for o in env.get("VP_CORS_ORIGINS", "*").split(",") if o.strip()
            ),
            rate_limit_per_minute=int(env.get("VP_RATE_LIMIT_PER_MINUTE", 0)),
            trust_proxy=env.get("VP_TRUST_PROXY", "") == "1",
        )
