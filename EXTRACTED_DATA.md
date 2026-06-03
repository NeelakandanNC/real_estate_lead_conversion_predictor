# Extracted survey data — ANAROCK Homebuyer Sentiment Surveys

Source PDFs in this repo: `H1-2022.pdf`, `H1_2023.pdf`, `H2_2023.pdf`, `H1_2024.pdf`, `H1_2025.pdf`.
Machine-readable version of everything below: **`priors.py`** (the canonical input for `generate_synthetic_data.py`).

## How this was extracted (and why it's trustworthy)

These reports are **chart-heavy**. The percentage labels in the donuts and stacked
bars are positioned as free-floating text, so `pdftotext` reads them in the wrong
order — it will happily hand you a 6-number income split that maps to the wrong
bands. So every distribution here was **read off the rendered page image**, not
trusted from the text layer:

1. `pdftotext -layout` for the narrative + the zone tables (those are real tables and extract cleanly).
2. `pdftoppm -png` to render each page; numbers on every **chart** were read visually from the image (cropping to ~300 DPI where the thumbnail was ambiguous).
3. `H1_2023.pdf` is fully image-based (zero text layer) → read entirely from rendered pages.

**Correction found this way:** the H1-2025 income split was previously recorded as
`20/14/14/12/20/20`. The rendered donut clearly reads **`20/20/20/14/14/12`**. This
matters: it moves ~14 pts of buyers out of the top income bands, so the affordability
coupling caps ticket sizes lower. Fixed in `priors.py` and `CLAUDE.md`.

## Survey coverage

| Edition | Respondents | Age | Gender (M/F) | Cities | Publisher |
|---|---|---|---|---|---|
| H1-2022 | 5,500 | 24–76 | 50/50 | 14 | CII–ANAROCK |
| H1-2023 | 5,218 | 23–78 | 50/50 | 14 | ANAROCK |
| H2-2023 | 5,510 | 22–76 | 50/50 | 14 | FICCI–ANAROCK |
| H1-2024 | 7,615 | 24–78 | 50/50 | 14 | FICCI–ANAROCK |
| H1-2025 | 8,250 | 24–78 | 50/50 | 14 | ANAROCK |

**H1-2025 is the PRIMARY baseline** for the generator. Others are for trend / sensitivity.

---

## 1. Annual family income (%) — VISUALLY VERIFIED

| Band | H1-2022 | H1-2023 | H2-2023 | H1-2024 | **H1-2025** |
|---|---|---|---|---|---|
| Under ₹10L | 22 | 22 | 22 | 20 | **20** |
| ₹11–15L | 20 | 20 | 20 | 22 | **20** |
| ₹16–20L | 22 | 22 | 22 | 22 | **20** |
| ₹21–25L | 12 | 12 | 12 | 12 | **14** |
| ₹26–35L | 12 | 12 | 12 | 12 | **14** |
| Above ₹35L | 12 | 12 | 12 | 12 | **12** |

Stable 2022→2024; H1-2025 shifts a little out of the ₹11–20L bands into ₹21–35L. Top band flat at 12% throughout. Gender 50/50 every edition.

---

## 2. Budget preference (%) — VISUALLY VERIFIED (full time series off the H1-2025 stacked bar)

| Band | Pre-COVID | H1-20 | H2-20 | H1-21 | H2-21 | H1-22 | H2-22 | H1-23 | H2-23 | H1-24 | H2-24 | **H1-25** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| <₹45L | 31 | 36 | 40 | 27 | 25 | 28 | 29 | 25 | 21 | 22 | 20 | **17** |
| ₹45–90L | 42 | 37 | 29 | 35 | 37 | 34 | 32 | 35 | 33 | 33 | 27 | **25** |
| ₹90L–1.5Cr | 18 | 16 | 20 | 25 | 26 | 24 | 26 | 24 | 26 | 28 | 34 | **36** |
| ₹1.5–2.5Cr | 6 | 8 | 7 | 9 | 8 | 10 | 9 | 10 | 12 | 10 | 11 | **12** |
| >₹2.5Cr | 3 | 3 | 4 | 4 | 4 | 4 | 4 | 6 | 8 | 7 | 9 | **10** |

**Headline trend:** affordable (<45L) collapsing 40%→17%; premium (90L–1.5Cr) doubling 18%→36%. This is the central demand-shift story for the pitch.
**Caveat:** the H1-2024 *report text* claims affordable = 18% / 45–90L = 35%, but its own *chart* (and the H1-2025 chart) render H1-2024 affordable ≈ 22%. We use the chart-consistent value.

---

## 3. BHK preference (%) — VISUALLY VERIFIED

### Pan-India
| | 1BHK | 2BHK | 3BHK | 4BHK+ |
|---|---|---|---|---|
| H1-2022 | 11 | 38 | 44 | 7 |
| H1-2023 | 6 | 39 | 48 | 7 |
| H2-2023 | 4 | 38 | 50 | 8 |
| H1-2024 | 4 | 39 | 51 | 6 |
| **H1-2025** | **8** | **40** | **45** | **7** |

### City-wise, H1-2025 (PRIMARY) — 1 / 2 / 3 / 4+ BHK
| City | 1BHK | 2BHK | 3BHK | 4BHK+ |
|---|---|---|---|---|
| Bengaluru | 8 | 34 | 48 | 10 |
| Chennai | 6 | 35 | 53 | 6 |
| Delhi-NCR | 5 | 36 | 53 | 6 |
| Hyderabad | 2 | 38 | 55 | 5 |
| Kolkata | 4 | 46 | 46 | 4 |
| Mumbai-MMR | 20 | 40 | 36 | 4 |
| Pune | 9 | 41 | 47 | 3 |
| Ahmedabad | 4 | 29 | 60 | 7 |

(Full city-wise tables for H1-2022 / H1-2023 / H2-2023 / H1-2024 are in `priors.py:BHK_CITY_DIST`.)
Notes: Mumbai-MMR is the only metro with strong 1BHK demand (≈20%). Kolkata/MMR/Pune lean 2BHK; everywhere else 3BHK dominates. **Ahmedabad has BHK data but NO zone ₹/sqft table** (see §6 gap).
Kolkata H1-2023 source misprints 3BHK as "47%" (labels sum to 110) — bar width ⇒ 37%, recorded as `6/52/37/5`.

---

## 4. Buyer intent — end-use vs investment (%) — VISUALLY VERIFIED

| | Pre | H1-20 | H2-20 | H1-21 | H2-21 | H1-22 | H2-22 | H1-23 | H2-23 | H1-24 | H2-24 | **H1-25** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| End-use | 67 | 59 | 74 | 71 | 68 | 69 | 71 | 68 | 64 | 67 | 63 | **65** |
| Investment | 33 | 41 | 26 | 29 | 32 | 31 | 29 | 32 | 36 | 33 | 37 | **35** |

H1-2024 investor sub-intent (only edition that splits it): **rental income 57% / build asset 23% / sell on appreciation 20%**.

---

## 5. Other marginals (per edition)

**Best asset class for investment (%)** — RE / Stock / Gold / FD
- H1-2022: 59 / 28 / 7 / 6 · H1-2023: 60 / 27 / 5 / 8 · H2-2023: 57 / 29 / 6 / 8 · H1-2024: 59 / 30 / 5 / 6 · **H1-2025: 63 / 22 / 7 / 8**

**Preferred construction stage — ready-to-move : new-launch ratio**
- H1-20 46:18 · H1-21 32:21 · H1-22 30:25 · H1-23 28:27 · H2-23 23:24 · H1-24 20:25 · **H1-25 16:29**
- H1-2025 full 4-way split: new launch 29% / ready-to-move 16% / ready ≤6mo 30% / ready ≤1yr 25%.

**Home-loan-rate sensitivity (H1-2024, % reporting HIGH impact on buying)**
- <8.5%: 12 · 8.5–9%: 35 · 9–9.5%: 87 · >9.5%: 94. (Repo cuts in H1-2025 lifted confidence: 83% more confident, 87% more likely to take a loan.)

**Avg flat size, top-7 (sqft):** 2019 1,145 · 2020 1,167 · 2021 1,170 · 2022 1,175 · 2023 1,300 · H1-2024 1,513.

---

## 6. Property side — zone-wise 2BHK budget + ₹/sqft (the persona↔property bridge)

Full **H1-2025** table (7 cities, 36 zones) is in `priors.py:ZONE_TABLE['H1-2025']` — verified against the rendered "More About Your City" pages. Each row = average all-in **2BHK ticket range** + **average ₹/sqft**, which lets the generator back out implied carpet area and scale to other BHKs.

Example (H1-2025): South Central Mumbai 3.3–4.5Cr @ ₹44,000/sqft (top) down to Kolkata West 35–45L @ ₹4,850/sqft (bottom). MMR new-supply 58,900 (−24% YoY); NCR 29,900 (+23%).

**Price escalation** (₹/sqft, central zones, 2022→2025) is in `priors.py:ZONE_RATE_PSF_SERIES` — e.g. Gurgaon 6,350→11,000 (+73%), Noida 5,100→9,600, Central Bengaluru 10,500→16,650, Central Hyderabad 6,400→10,280. Useful for the "don't pool ticket sizes across years/cities" point.

### Gaps / cautions to carry into the generator
- **Ahmedabad** appears in BHK preference but has **no zone ₹/sqft table** in any edition → cannot place Ahmedabad properties from this data alone. Either drop Ahmedabad buyers or source ₹/sqft elsewhere.
- Zone tables cover the **top 7 metros only** (MMR, NCR, Bengaluru, Pune, Chennai, Kolkata, Hyderabad). The surveys span "14 cities" but only 7 get the property-side table.
- Budget/income/BHK are **marginals**, not a joint. The income×BHK×ticket joint is *imposed* by the 4–5× affordability coupling in the generator — it is NOT in any survey.
- Minor source rounding: a few city-BHK rows sum to 99–101%; normalize before sampling.

---

## Provenance / reproduce

```bash
# text layer + zone tables
for f in H1_2025 H1_2024 H2_2023 "H1-2022"; do pdftotext -layout "$f.pdf" "extracted/$f.txt"; done
# rendered pages for every chart (H1_2023 has no text layer at all)
for f in H1_2025 H1_2024 H2_2023 H1_2023 "H1-2022"; do pdftoppm -png -r 130 "$f.pdf" "extracted/${f}_img/p"; done
```
Rendered page images live under `extracted/<edition>_img/`. Text dumps under `extracted/*.txt`.
