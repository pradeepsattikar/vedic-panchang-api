"""Fingerprint of everything that can change an answer, for caches in front of the API.

Sent as the ``X-Data-Fingerprint`` header and in ``/v1/meta``. A cache that files answers under
it never serves an answer from an older deploy, without anyone remembering a version bump.
"""

import hashlib
from functools import cache
from importlib.metadata import version
from pathlib import Path

_PACKAGE = Path(__file__).resolve().parents[1]  # src/vedic_panchang
_DEPENDENCIES = ("pyswisseph", "tzdata")  # ephemeris and timezone data


@cache
def data_fingerprint() -> str:
    """Short hash of the package's code and data files plus the ephemeris and timezone versions.

    Any deploy that could change a value changes it; a speed-only code change does too, which
    only means caches refill once."""
    digest = hashlib.sha256()
    for path in sorted(_PACKAGE.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            digest.update(path.relative_to(_PACKAGE).as_posix().encode())
            digest.update(path.read_bytes())
    for name in _DEPENDENCIES:
        digest.update(f"{name}=={version(name)}".encode())
    return digest.hexdigest()[:16]
