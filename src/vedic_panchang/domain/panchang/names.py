"""Canonical identifiers and English transliterations of Panchang elements.

IDs are stable API identifiers; the names are default English transliterations. Clients
should localise by ID rather than by name.
"""

TITHIS = (
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima",
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Amavasya",
)  # fmt: skip

NAKSHATRAS = (
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishtha",
    "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
)  # fmt: skip

YOGAS = (
    "Vishkambha", "Preeti", "Ayushman", "Saubhagya", "Shobhana",
    "Atiganda", "Sukarma", "Dhriti", "Shula", "Ganda",
    "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra",
    "Siddhi", "Vyatipata", "Variyan", "Parigha", "Shiva",
    "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma",
    "Indra", "Vaidhriti",
)  # fmt: skip

_MOVABLE_KARANAS = ("Bava", "Balava", "Kaulava", "Taitila", "Garaja", "Vanija", "Vishti")
_FIXED_KARANAS_END = ("Shakuni", "Chatushpada", "Naga")

VARAS = (
    "Somavara",
    "Mangalavara",
    "Budhavara",
    "Guruvara",
    "Shukravara",
    "Shanivara",
    "Ravivara",
)  # fmt: skip  (indexed by Python weekday, Monday = 0)


def slug(name: str) -> str:
    return name.lower().replace(" ", "-")


def paksha(tithi_index: int) -> str:
    return "shukla" if tithi_index < 15 else "krishna"


def tithi_id(tithi_index: int) -> str:
    return f"{paksha(tithi_index)}-{slug(TITHIS[tithi_index])}"


def karana_name(karana_index: int) -> str:
    """Name of karana 0..59 (half-tithis of the lunar month)."""
    if karana_index == 0:
        return "Kimstughna"
    if karana_index >= 57:
        return _FIXED_KARANAS_END[karana_index - 57]
    return _MOVABLE_KARANAS[(karana_index - 1) % 7]
