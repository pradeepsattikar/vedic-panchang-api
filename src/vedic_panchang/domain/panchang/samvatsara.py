"""Samvatsara: the name of the year in the 60-year cycle (Prabhava ... Akshaya).

Two conventions, both returned with every daily answer (added 2026-10-27):

- **Shaka (Maharashtra, South India):** a fixed cycle on the Shaka year, which begins at Chaitra
  Shukla Pratipada. Shaka 1948 (2026-27) is Parabhava, number 40.
- **Vikram (North India), Barhaspatya:** the cycle follows Jupiter. A Jovian year is the time
  Jupiter's mean motion takes through one sign: 1,577,917,828 days / (364,220 revolutions x 12)
  = 361.0267 days (Surya Siddhanta). It is about four days shorter than a solar year, so about
  once in 85 years a name is skipped (kshaya). The Vikram year, which begins at Chaitra Shukla
  Pratipada, takes the Jovian samvatsara in force at Mesha Sankranti of that spring.
  The phase is matched to Drik Panchang: its change times 2022-2032 lie within 20 minutes of
  this cycle, and its Vikram year names 2079-2088 (including the skip of Durmati in 2028) match.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from vedic_panchang.astronomy import ephemeris as eph
from vedic_panchang.astronomy.julian import from_jd, to_jd
from vedic_panchang.domain.festivals.calendar import sankrantis
from vedic_panchang.domain.panchang import names

JOVIAN_YEAR_DAYS = 1_577_917_828 / (364_220 * 12)

# The change from Siddharthi (53) to Raudra, placed so that Drik Panchang's ten change times
# 2022-2032 all lie within 20 minutes of the cycle (Drik shows 2026-04-21 15:53 IST).
_ANCHOR_JD = to_jd(datetime(2026, 4, 21, 10, 3, tzinfo=UTC))
_ANCHOR_NEXT = 53  # 0-based index of the samvatsara that began then (Raudra)


@dataclass(frozen=True)
class Samvatsara:
    number: int  # 1 = Prabhava ... 60 = Akshaya
    id: str
    name: str


def samvatsara(index: int) -> Samvatsara:
    """From a 0-based index in the cycle."""
    name = names.SAMVATSARAS[index % 60]
    return Samvatsara(index % 60 + 1, name.lower(), name)


def shaka_samvatsara(shaka_year: int) -> Samvatsara:
    return samvatsara(shaka_year + 11)


def jovian_index(jd: float) -> int:
    """0-based index of the Barhaspatya samvatsara in force at ``jd``."""
    elapsed = (jd - _ANCHOR_JD) // JOVIAN_YEAR_DAYS
    return (_ANCHOR_NEXT + int(elapsed)) % 60


def vikram_samvatsara(vikram_year: int, ayanamsha: eph.Ayanamsha) -> Samvatsara:
    gregorian = vikram_year - 57  # the spring in which the Vikram year begins
    mesha = next(
        s.jd
        for s in sankrantis(gregorian, ayanamsha)
        if s.sign == 0 and from_jd(s.jd, UTC).year == gregorian
    )
    return samvatsara(jovian_index(mesha))
