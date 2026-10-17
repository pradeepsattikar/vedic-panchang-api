"""Find when a cyclic angle (e.g. Moon-Sun elongation) crosses segment boundaries.

Every Panchang element is "which equal segment of 360 degrees is this angle in": Tithi is
the elongation in 12-degree segments, Nakshatra the Moon's longitude in 13 deg 20' segments,
and so on. A span starts and ends where the angle crosses a segment boundary.
"""

from collections.abc import Callable
from dataclasses import dataclass

AngleFn = Callable[[float], float]  # Julian day (UT) -> angle in degrees [0, 360)

# Search horizon either side of a reference instant. The longest span (a Tithi or Yoga)
# lasts about 1.1 days, and within 2 days no angle moves anywhere near 180 degrees, so
# angles can be unwrapped unambiguously around the reference.
_SEARCH_DAYS = 2.0
_BISECTION_STEPS = 40  # 33 days / 2**40 is well under a millisecond


@dataclass(frozen=True)
class RawSpan:
    index: int  # 0-based segment index
    start_jd: float
    end_jd: float


def _unwrapped(angle_fn: AngleFn, jd: float, ref_angle: float) -> float:
    delta = (angle_fn(jd) - ref_angle + 180.0) % 360.0 - 180.0
    return ref_angle + delta


def _crossing(angle_fn: AngleFn, lo: float, hi: float, ref_angle: float, target: float) -> float:
    """Bisect for the instant in [lo, hi] at which the unwrapped angle reaches ``target``."""
    if not _unwrapped(angle_fn, lo, ref_angle) < target <= _unwrapped(angle_fn, hi, ref_angle):
        raise ArithmeticError("segment boundary not bracketed by the search window")
    for _ in range(_BISECTION_STEPS):
        mid = (lo + hi) / 2.0
        if _unwrapped(angle_fn, mid, ref_angle) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def _span_at(
    angle_fn: AngleFn, segment_deg: float, count: int, jd: float, search_days: float
) -> RawSpan:
    angle = angle_fn(jd)
    index = int(angle // segment_deg) % count
    start = _crossing(angle_fn, jd - search_days, jd, angle, index * segment_deg)
    end = _crossing(angle_fn, jd, jd + search_days, angle, (index + 1) * segment_deg)
    return RawSpan(index, start, end)


def spans_over(
    angle_fn: AngleFn,
    segment_deg: float,
    window_start: float,
    window_end: float,
    search_days: float = _SEARCH_DAYS,
) -> list[RawSpan]:
    """All segments overlapping [window_start, window_end), in time order.

    ``search_days`` must exceed the longest span (e.g. ~31 days for the Sun's Rashi) while the
    angle moves well under 180 degrees in that time."""
    count = round(360.0 / segment_deg)
    spans = [_span_at(angle_fn, segment_deg, count, window_start, search_days)]
    while spans[-1].end_jd < window_end:
        previous = spans[-1]
        nxt = _span_at(angle_fn, segment_deg, count, previous.end_jd + 1e-6, search_days)
        # The next span starts exactly where the previous one ended.
        spans.append(RawSpan(nxt.index, previous.end_jd, nxt.end_jd))
    return spans


def crossing_near(angle_fn: AngleFn, target: float, guess_jd: float, mean_speed: float) -> float:
    """Instant near ``guess_jd`` at which a steadily increasing angle passes ``target``.

    For events far apart (e.g. new moons), the guess is refined with the mean angular
    speed (degrees/day) before bisecting within the usual search horizon.
    """
    jd = guess_jd
    for _ in range(3):
        degrees_past = (angle_fn(jd) - target + 180.0) % 360.0 - 180.0
        jd -= degrees_past / mean_speed
    return _crossing(angle_fn, jd - _SEARCH_DAYS, jd + _SEARCH_DAYS, target, target)
