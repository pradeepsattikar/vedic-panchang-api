# How the Vedic Panchang API calculates

This document explains, in plain English, every rule the API uses: the daily Panchang, timings,
festivals, puja times and muhurtas. Numbers here are the ones in the code. Last updated
2026-10-18 (API 0.3.0).

**Ground rules**

- Every value is **calculated** from the positions of the Sun, Moon and planets. Nothing is copied
  from a list, estimated, or produced by AI.
- Rules that differ between traditions are kept as **data files**, not hidden in code:
  `rules/data/profiles.toml`, `rules/data/festivals/north-indian-smarta.toml` and
  `rules/data/muhurta/north-indian-smarta.toml`. Each file has a `rule_version`, and every
  response says which versions it used.
- When something cannot be calculated (for example, no sunrise near the poles), the API says so.
  It never shows `00:00`, a blank, or another city's value instead.
- Results are checked against **Drik Panchang** in automated tests (see "Verification" at the end).

**Tradition used:** North Indian, Purnimanta month names, Smarta festival observance.

---

## 1. Astronomy and time

| Item | Rule |
|---|---|
| Astronomy engine | Swiss Ephemeris (pyswisseph), built-in Moshier ephemeris |
| Zodiac | Sidereal, with the **Lahiri (Chitrapaksha)** ayanamsha |
| Places | A city from GeoNames (Canada, US, India; population 5,000 or more) or any latitude, longitude and time zone |
| Time zones | IANA time zones from the bundled `tzdata` package, so daylight-saving rules are the latest (for example, British Columbia's permanent daylight time from March 2026) |
| Times | Local time with the UTC offset, to the second. Apps show them rounded to the nearest minute, as Drik Panchang does |
| Supported dates | 1 January 2020 to 31 December 2035 |

### The Panchang day

- A **Panchang day runs from local sunrise to the next local sunrise**.
- Values labelled **"at sunrise"** are those in force at that day's sunrise. Every change during
  the Panchang day is also listed, with its full local date and time.
- Near the poles, where the Sun may not rise, the civil day (midnight to midnight) is used
  and "at sunrise" values are marked unavailable.

### Sunrise, sunset, moonrise, moonset

| Event | How it is measured | Which day it belongs to |
|---|---|---|
| Sunrise, sunset | When the **top edge** of the Sun touches the horizon, with standard atmospheric refraction | The local calendar date |
| Moonrise, moonset | When the **centre** of the Moon crosses the horizon, without refraction (Drik Panchang's convention) | The Panchang day (sunrise to next sunrise). A moonrise at 2 AM belongs to the previous date and shows its own date |

If the Moon does not rise (or set) within the Panchang day, the API reports **"no moonrise"**
together with the time of the next one. This is a normal result, not an error.

---

## 2. The five elements (Panchang)

"Sun" and "Moon" below mean their **sidereal longitudes** (0–360°).

| Element | Rule | Count |
|---|---|---|
| **Tithi** | Moon minus Sun, divided into 12° parts | 30 (1–15 Shukla, 16–30 Krishna; 15 = Purnima, 30 = Amavasya) |
| **Paksha** | Tithis 1–15 are Shukla (waxing), 16–30 Krishna (waning) | 2 |
| **Nakshatra** | Moon divided into 13°20′ parts | 27 (each has 4 padas of 3°20′) |
| **Yoga** | Sun plus Moon, divided into 13°20′ parts | 27 |
| **Karana** | Moon minus Sun, divided into 6° parts (half a Tithi) | 60 per month: Kimstughna; then Bava, Balava, Kaulava, Taitila, Garaja, Vanija, Vishti repeated 8 times; then Shakuni, Chatushpada, Naga |
| **Vara** | Weekday of the Panchang day's sunrise | 7 |

**Bhadra** is the time of the Vishti Karana.

### Other details on the Panchang page

| Item | Rule |
|---|---|
| **Lunar month (Amanta)** | New moon to new moon. Named after the sign the Sun enters during the month: the month in which the Sun enters Mesha is Chaitra |
| **Adhika (extra) month** | A lunar month in which the Sun enters no new sign. It takes the name of the following month |
| **Purnimanta month** | Full moon to full moon. The Shukla half keeps its Amanta name; the Krishna half takes the next month's name |
| **Vikram Samvat** | Calendar year + 57, from Chaitra Shukla Pratipada. Dates from January to April that are still in Pausha, Magha or Phalguna use calendar year + 56 |
| **Shaka Samvat** | Vikram Samvat − 135 |
| **Ritu** (Vedic) | By Amanta month, two months each: Chaitra–Vaishakha Vasanta, Jyeshtha–Ashadha Grishma, Shravana–Bhadrapada Varsha, Ashwin–Kartika Sharad, Margashirsha–Pausha Hemanta, Magha–Phalguna Shishira |
| **Ayana** | Uttarayana while the Sun is in Makara, Kumbha, Meena, Mesha, Vrishabha or Mithuna; otherwise Dakshinayana |
| **Surya Rashi / Chandra Rashi** | Sun / Moon divided into 30° signs (Mesha to Meena), with the time of each change |
| **Surya Nakshatra** | Sun divided into 13°20′ parts, with the time of each change |
| **Sankranti** | The moment the Sun enters a new sign |

---

## 3. Daily timings

"Daytime" is sunrise to sunset. "Night" is sunset to the next sunrise (for Brahma Muhurta:
24 hours minus daytime).

### Times to avoid: Rahu Kalam, Yamaganda, Gulika Kalam

Daytime is split into **8 equal parts**. The weekday decides which part:

| Weekday | Rahu Kalam | Yamaganda | Gulika Kalam |
|---|---|---|---|
| Monday | 2nd | 4th | 6th |
| Tuesday | 7th | 3rd | 5th |
| Wednesday | 5th | 2nd | 4th |
| Thursday | 6th | 1st | 3rd |
| Friday | 4th | 7th | 2nd |
| Saturday | 3rd | 6th | 1st |
| Sunday | 8th | 5th | 7th |

### Good times

| Timing | Rule |
|---|---|
| **Abhijit Muhurta** | Daytime split into 15 muhurtas; the **8th** one. **Not given on Wednesdays** (traditionally avoided) |
| **Brahma Muhurta** | Night (24 h − daytime) split into 15; from **2 night-muhurtas before sunrise** to **1 before sunrise** |

---

## 4. Festivals and vrats

### How the date is chosen (lunar festivals)

Each festival has a lunar month, a Tithi and a **kala** (the part of the day in which the Tithi
must be present):

| Kala | Part of the day |
|---|---|
| Sunrise | The moment of sunrise |
| Sunset | The moment of sunset |
| Moonrise | The moment of moonrise within the Panchang day |
| Arunodaya | 96 minutes (4 ghatis) before sunrise |
| Purvahna | First half of daytime |
| Madhyahna | 3rd of 5 equal parts of daytime |
| Aparahna | 4th of 5 equal parts of daytime |
| Pradosh | First fifth of the night after sunset |
| Nishita | 8th of 15 equal parts of the night (around midnight) |

1. The festival is on the **local date whose kala contains the Tithi**.
2. If the Tithi touches the kala on **two days**, a tie-break decides: by default the **first**
   day for sunrise and moonrise festivals, otherwise the day on which the Tithi covers **more of
   the kala**.
3. If it touches the kala on **neither** day, the festival is on the day the Tithi is present
   **at sunrise**. A Tithi that touches no sunrise is placed in the Panchang day in which it begins.
4. **Yearly festivals** happen only in regular (Nija) months, never in an Adhika month. Monthly
   observances happen every month. Padmini and Parama Ekadashi happen only in an Adhika month.
5. For **Raksha Bandhan**, time under Bhadra does not count as part of the kala.
6. Because the kala is judged in **local time**, a festival can fall on a different date in
   North America than in India. This is correct, not an error.

### Solar festivals

**Sankrantis** (including Makar Sankranti) fall on the date of the Sun's entry into the sign. If
the entry happens **after sunset**, they are observed the **next day**.

### The festival list

Months are **Amanta** names (Krishna-paksha festivals carry the next month's name in the North
Indian calendar; for example, Diwali is "Ashwin Amavasya" here and "Kartika Amavasya" in the North).
Tithi numbers: 1–15 Shukla, 16–30 Krishna.

| Festival | Month | Tithi | Kala |
|---|---|---|---|
| Vasant Panchami | Magha | 5 | Purvahna |
| Maha Shivaratri | Magha | 29 (K. Chaturdashi) | Nishita |
| Holika Dahan | Phalguna | 15 (Purnima) | Pradosh |
| Holi | Phalguna | 16 (K. Pratipada) | Aparahna |
| Chaitra Navratri / Gudi Padwa / Ugadi | Chaitra | 1 | Sunrise |
| Ram Navami | Chaitra | 9 | Madhyahna |
| Hanuman Jayanti | Chaitra | 15 | Sunrise |
| Akshaya Tritiya | Vaishakha | 3 | Purvahna |
| Vat Savitri Vrat | Vaishakha | 30 (Amavasya) | Sunrise |
| Guru Purnima | Ashadha | 15 | Sunrise |
| Hariyali Teej | Shravana | 3 | Sunrise |
| Nag Panchami | Shravana | 5 | Sunrise |
| Raksha Bandhan | Shravana | 15 | Aparahna, outside Bhadra |
| Krishna Janmashtami | Shravana | 23 (K. Ashtami) | Nishita |
| Hartalika Teej | Bhadrapada | 3 | Sunrise |
| Ganesh Chaturthi | Bhadrapada | 4 | Madhyahna |
| Anant Chaturdashi | Bhadrapada | 14 | Sunrise |
| Pitru Paksha begins | Bhadrapada | 16 | Aparahna |
| Sarva Pitru Amavasya | Bhadrapada | 30 | Aparahna |
| Sharad Navratri begins | Ashwin | 1 | Sunrise |
| Durga Ashtami | Ashwin | 8 | Sunrise |
| Maha Navami | Ashwin | 9 | Sunrise |
| Dussehra (Vijayadashami) | Ashwin | 10 | Aparahna |
| Sharad Purnima | Ashwin | 15 | Moonrise |
| Karwa Chauth | Ashwin | 19 (K. Chaturthi) | Moonrise |
| Ahoi Ashtami | Ashwin | 23 | Pradosh |
| Dhanteras | Ashwin | 28 (K. Trayodashi) | Pradosh |
| Naraka Chaturdashi (Choti Diwali) | Ashwin | 29 | Arunodaya |
| Diwali (Lakshmi Puja) | Ashwin | 30 (Amavasya) | Pradosh |
| Govardhan Puja | Kartika | 1 | Aparahna |
| Bhai Dooj | Kartika | 2 | Aparahna |
| Chhath Puja | Kartika | 6 | Sunset |
| Kartik Purnima (Dev Deepawali) | Kartika | 15 | Sunrise |
| Gita Jayanti | Margashirsha | 11 | Sunrise |
| The 24 Ekadashis (named by month) | Every month | 11 and 26 | Sunrise |
| Purnima / Amavasya | Every month | 15 / 30 | Sunrise |
| Sankashti Chaturthi | Every month | 19 | Moonrise |
| Vinayaka Chaturthi | Every month except Bhadrapada | 4 | Madhyahna |
| Pradosh Vrat (Shukla / Krishna) | Every month | 13 / 28 | Pradosh |
| Masik Shivaratri | Every month except Magha | 29 | Nishita |
| Makar Sankranti; the other Sankrantis | Sun enters Makara; each sign | — | Solar (see above) |

---

## 5. Puja times

For festivals with a customary puja or observance time, the API lists those times, most
important first. Unless stated otherwise, a window is **cut to the time the festival's Tithi is
present**. "Day parts" use daytime (sunrise to sunset); "night parts" use sunset to the next
sunrise. One ghati = 24 minutes.

| Puja time | Rule | Used for |
|---|---|---|
| Pratahkala | First fifth of daytime | Nag Panchami, Hartalika Teej, Govardhan Puja |
| Purvahna | First half of daytime (not cut to the Tithi, as Drik does) | Vasant Panchami, Akshaya Tritiya |
| Madhyahna | 3rd of 5 parts of daytime | Ganesh Chaturthi, Vinayaka Chaturthi, Ram Navami |
| Aparahna | 4th of 5 parts of daytime | Bhai Dooj, Dussehra, Pitru Paksha, Sarva Pitru Amavasya |
| Sayankala | 5th of 5 parts of daytime | Govardhan Puja |
| Pradosh Kaal | First fifth of the night | Pradosh Vrat, Diwali, Dhanteras, Hartalika Teej |
| Nishita Kaal | 8th of 15 parts of the night | Janmashtami, Maha and Masik Shivaratri, Diwali, Sharad Purnima |
| Night prahars 1–4 | The night in 4 equal quarters (not cut to the Tithi) | Maha Shivaratri |
| Kutup / Rohina Muhurat | 8th / 9th of the 15 daytime muhurtas | Shraddha days |
| Abhijit Muhurat | 8th of the 15 daytime muhurtas | Navratri (Ghatasthapana alternative) |
| Vijay Muhurat | 11th of the 15 daytime muhurtas | Dussehra |
| Lakshmi Puja / Dhanteras Puja | Pradosh Kaal, while Amavasya (or Trayodashi) is present and **Vrishabha lagna** (a fixed sign) is rising. If Vrishabha does not rise in that time, Pradosh Kaal while the Tithi is present | Diwali, Dhanteras |
| Ghatasthapana | First third of daytime while Pratipada is present. For Sharad Navratri, only while **Kanya lagna** is rising | Chaitra and Sharad Navratri |
| Sandhi Puja | Last 24 minutes of Ashtami and first 24 minutes of Navami | Durga Ashtami |
| Rakhi time | Sunrise to the end of Pradosh Kaal, while Purnima is present and **outside Bhadra** (the longest such part) | Raksha Bandhan |
| Holika Dahan | Pradosh Kaal while Purnima is present and free of Bhadra. If Bhadra covers Pradosh but ends before midnight, from Bhadra's end to midnight. If Bhadra lasts beyond midnight, no time is given | Holika Dahan |
| Abhyang Snan | Moonrise to sunrise, while Chaturdashi is present | Naraka Chaturdashi |
| Fasting time (Upavasa) | Sunrise to moonrise | Karwa Chauth |
| Evening puja | First tenth of the night | Karwa Chauth, Ahoi Ashtami |
| Star sighting | One ghati (24 minutes) after sunset | Ahoi Ashtami |
| Moonrise | Moonrise within the Panchang day | Karwa Chauth, Sankashti, Purnima, Sharad Purnima |
| Sandhya / Usha Arghya | Sunset / the next sunrise | Chhath Puja |
| Dev Deepawali | Pradosh Kaal (not cut to the Tithi) | Kartik Purnima |
| Anant Chaturdashi puja | From sunrise while Chaturdashi is present | Anant Chaturdashi |
| **Parana** (breaking the Ekadashi fast) | On the **next day**, never during **Hari Vasara** (the first quarter of Dwadashi). In the first fifth of daytime, before Dwadashi ends. If Hari Vasara lasts beyond that, in Aparahna instead | Every Ekadashi |
| Punya Kaal | From the Sun's entry into Makara for 40 ghatis, within daylight | Makar Sankranti |

The **rising sign (lagna)** is the sidereal ascendant at the place, calculated by Swiss Ephemeris.

Festivals without a fixed muhurta in the tradition (Holi, Guru Purnima, Hanuman Jayanti, Vat Savitri,
Hariyali Teej, Maha Navami, Gita Jayanti, Amavasya, monthly Sankranti) have no puja time.

---

## 6. Muhurtas (Vivah, Griha Pravesh)

These are **general muhurtas** ("Panchang Shuddhi"). They are **not based on anyone's birth
chart**, and the lagna is not checked. The app shows this disclaimer and advises confirming
the time with a family priest.

### How a muhurta window is found

1. Each Panchang day is cut into pieces at every moment that could change the answer:
   changes of Tithi, Nakshatra (or Nakshatra pada), Yoga, Bhadra, the Sun's sign, lunar month,
   Chaturmas, Guru/Shukra setting, and sunrise.
2. Each piece is checked against the purpose's rules (below).
3. Good pieces next to each other **within the same Panchang day** are joined into one window.
   Windows shorter than **5 minutes** are dropped.

### Rules

| Rule | Vivah (marriage) | Griha Pravesh (new home, Vastu) |
|---|---|---|
| Nakshatras allowed | Rohini, Mrigashira, Magha, Uttara Phalguni, Hasta, Swati, Anuradha, Mula, Uttara Ashadha, Uttara Bhadrapada, Revati | Rohini, Mrigashira, Uttara Phalguni, Chitra, Anuradha, Uttara Ashadha, Uttara Bhadrapada, Revati |
| Tithis allowed | All except Shukla Pratipada, Dwitiya and Shashthi; Krishna Saptami, Ashtami and Chaturdashi; and Amavasya | Shukla 2, 3, 5, 7, 10, 11, 13 and Krishna 2, 3, 5, 7, 10, 11 |
| Weekdays | All | Not Sunday or Tuesday |
| Yogas avoided | Vishkambha, Atiganda, Shula, Ganda, Vyaghata, Vajra, Vyatipata, Parigha, Vaidhriti | Not checked |
| Bhadra (Vishti Karana) | Avoided | Not checked |
| Gandanta | Avoided: the first pada of Ashwini, Magha and Mula, and the last pada of Revati (and of Ashlesha and Jyeshtha) | Not checked |
| Lunar months | Any regular month | Only Magha, Phalguna, Vaishakha, Jyeshtha, Kartika and Margashirsha (Amanta) |
| Adhika month | Avoided | Avoided |
| Sun's sign (Kharmas) | Not while the Sun is in Dhanu or Meena | Not checked |
| Chaturmas | Avoided: from the start of Ashadha Shukla Ekadashi to the end of Kartika Shukla Ekadashi | Not checked |
| Guru and Shukra asta | Avoided | Avoided |

### Guru and Shukra asta (planet "set" near the Sun)

A planet is **asta** when it is too close to the Sun to be seen. Following the classical
method, closeness is measured in **kalamsha**: the time gap between the planet and the Sun at
the place, in degrees of time (4 minutes = 1°).

- When the planet is **east** of the Sun (an evening star): the gap between the Sun's setting
  and the planet's setting.
- When it is **west** of the Sun (a morning star): the gap between the planet's rising and the
  Sun's rising.
- Both the Sun and the planet are measured by the **centre of the disc, without refraction**.
- The planet is asta when the gap is **below the limit**:
  - **Jupiter (Guru): 18**
  - **Venus (Shukra): 10**, or **8** while it is an evening star nearing inferior conjunction
- The check is made once a day: at sunset for an evening star, at sunrise for a morning star.

Because the gap depends on latitude, asta starts and ends on slightly different dates in
different cities, as on Drik Panchang. The limits were set so that Drik Panchang's published
Guru and Shukra asta dates for 2026 are reproduced.

---

## 7. Verification

Automated tests compare the API with readings taken from Drik Panchang:

| Area | What is checked | Result |
|---|---|---|
| Daily Panchang | 26 city-days in Toronto, Vancouver, New York, London, Mumbai and Pune: normal days, Diwali, daylight-saving changes, times after midnight, no-moonrise days, the 2028 leap day | Sunrise, sunset, Nakshatra ends and all timings within **1 minute**; moonrise and moonset within 1 minute; all names exact |
| Festivals | Published New Delhi dates, 2024–2026 | All dates match |
| Puja times | 28 Drik puja windows (Delhi, Brampton) | Within 1 minute |
| Muhurtas | Drik's 2026 lists for Ottawa | Griha Pravesh: all 32 days, 99.9% of minutes. Vivah: all days except three documented Drik inconsistencies, more than 99.5% of minutes |

### Known small differences (open questions)

- **Tithi end times** are 1–1.7 minutes later than Drik's, by the same amount everywhere. The cause
  is not the ephemeris, Delta T or apparent positions. Tests allow 2 minutes.
- **Sankranti moments** are about 8 minutes earlier than Drik's. Drik appears to use a slightly
  different Lahiri variant. This affects Sankranti times only, not Tithis or dates elsewhere.
  A decision on switching is pending.
- **Holika Dahan 2026:** the rules give 2 March; published calendars disagree (2 or 3 March).

---

## Glossary

| Term | Meaning |
|---|---|
| Amanta / Purnimanta | Lunar months ending at the new moon / at the full moon |
| Ayanamsha | The offset between the tropical and sidereal zodiacs |
| Ghati | 24 minutes (1/60 of a day) |
| Kala | A part of the day used for festival rules |
| Lagna | The zodiac sign rising on the eastern horizon at a moment |
| Muhurta | (a) 1/15 of daytime or night; (b) an auspicious time for an event |
| Nija / Adhika month | A regular month / an extra (leap) lunar month |
| Pada | A quarter of a Nakshatra (3°20′) |
| Panchang Shuddhi | Checking a time against the Panchang elements only (no birth chart) |
| Sidereal | Measured against the fixed stars (the Indian zodiac), not the seasons |
