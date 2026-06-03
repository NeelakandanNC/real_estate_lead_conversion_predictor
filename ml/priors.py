"""
All the numbers here are pulled straight from the ANAROCK Homebuyer Sentiment
Surveys (H1-2022 through H1-2025), and this is the one place the generator reads
them from. We sample from H1-2025 as the baseline, the older editions are kept
mostly for the trend story. Money is in INR (L = lakh, Cr = crore), and keep in
mind these are marginals only - the income-to-flat joint is something we impose
later, the survey itself never gives it.
"""

LAKH = 100_000
CRORE = 10_000_000

# Editions in chronological order (used as the x-axis for all time series).
PERIODS = ["Pre-COVID", "H1-2020", "H2-2020", "H1-2021", "H2-2021",
           "H1-2022", "H2-2022", "H1-2023", "H2-2023", "H1-2024",
           "H2-2024", "H1-2025"]

# Editions for which we have a full standalone report in this repo.
REPORT_EDITIONS = ["H1-2022", "H1-2023", "H2-2023", "H1-2024", "H1-2025"]

# ---------------------------------------------------------------------------
# 0. Survey metadata (sample size / coverage per edition)
# ---------------------------------------------------------------------------
SURVEY_META = {
    "H1-2022": {"respondents": 5500, "age": (24, 76), "gender": (50, 50), "cities": 14, "publisher": "CII-ANAROCK"},
    "H1-2023": {"respondents": 5218, "age": (23, 78), "gender": (50, 50), "cities": 14, "publisher": "ANAROCK"},
    "H2-2023": {"respondents": 5510, "age": (22, 76), "gender": (50, 50), "cities": 14, "publisher": "FICCI-ANAROCK"},
    "H1-2024": {"respondents": 7615, "age": (24, 78), "gender": (50, 50), "cities": 14, "publisher": "FICCI-ANAROCK"},
    "H1-2025": {"respondents": 8250, "age": (24, 78), "gender": (50, 50), "cities": 14, "publisher": "ANAROCK"},
}

# ---------------------------------------------------------------------------
# 1. Annual family income distribution (%) per edition
#    Bands: <10L, 11-15L, 16-20L, 21-25L, 26-35L, >35L
# ---------------------------------------------------------------------------
INCOME_BANDS = [
    ("under_10L",  (0,        10 * LAKH)),
    ("11_15L",     (11 * LAKH, 15 * LAKH)),
    ("16_20L",     (16 * LAKH, 20 * LAKH)),
    ("21_25L",     (21 * LAKH, 25 * LAKH)),
    ("26_35L",     (26 * LAKH, 35 * LAKH)),
    ("above_35L",  (35 * LAKH, 60 * LAKH)),  # open-ended; cap for sampling
]

INCOME_DIST = {
    # share order matches INCOME_BANDS. ALL VISUALLY VERIFIED from the income
    # donut on each report's Demographic Profiling page (pdftotext mis-floats
    # these numbers, so they were read from the rendered page images).
    "H1-2022": [22, 20, 22, 12, 12, 12],
    "H1-2023": [22, 20, 22, 12, 12, 12],
    "H2-2023": [22, 20, 22, 12, 12, 12],
    "H1-2024": [20, 22, 22, 12, 12, 12],
    "H1-2025": [20, 20, 20, 14, 14, 12],   # <- PRIMARY. CORRECTED: the donut reads
    # <10L 20 / 11-15L 20 / 16-20L 20 / 21-25L 14 / 26-35L 14 / >35L 12.
    # (CLAUDE.md's 20/14/14/12/20/20 was a text-extraction error.) Net vs H1-2024:
    # a modest shift out of the 11-20L bands into 21-35L; top >35L band unchanged
    # at 12%. Only ~26% of buyers earn >26L (NOT ~40%) -> gates ticket sizes lower.
}

# ---------------------------------------------------------------------------
# 2. Budget preference distribution (%) per edition
#    Bands: <45L, 45-90L, 90L-1.5Cr, 1.5-2.5Cr, >2.5Cr
# ---------------------------------------------------------------------------
BUDGET_BANDS = [
    ("under_45L",      (20 * LAKH,  45 * LAKH)),
    ("45_90L",         (45 * LAKH,  90 * LAKH)),
    ("90L_1_5Cr",      (90 * LAKH,  150 * LAKH)),
    ("1_5_2_5Cr",      (150 * LAKH, 250 * LAKH)),
    ("above_2_5Cr",    (250 * LAKH, 500 * LAKH)),  # open-ended; cap for sampling
]

# Full historical series, read column-by-column off the H1-2025 stacked-bar
# chart (the most complete one; every column verified from the rendered image
# and forced to sum to 100). Each inner list = one band across all 12 PERIODS.
BUDGET_SERIES = {
    #            Pre   H1-20 H2-20 H1-21 H2-21 H1-22 H2-22 H1-23 H2-23 H1-24 H2-24 H1-25
    "under_45L":   [31,  36,   40,   27,   25,   28,   29,   25,   21,   22,   20,   17],
    "45_90L":      [42,  37,   29,   35,   37,   34,   32,   35,   33,   33,   27,   25],
    "90L_1_5Cr":   [18,  16,   20,   25,   26,   24,   26,   24,   26,   28,   34,   36],
    "1_5_2_5Cr":   [6,   8,    7,    9,    8,    10,   9,    10,   12,   10,   11,   12],
    "above_2_5Cr": [3,   3,    4,    4,    4,    4,    4,    6,    8,    7,    9,    10],
}

# Per-edition marginal (what the generator samples from). H1-2025 is PRIMARY.
# Values = the verified time-series column for that edition (so DIST == SERIES).
BUDGET_DIST = {
    "H1-2022": [28, 34, 24, 10, 4],
    "H1-2023": [25, 35, 24, 10, 6],
    "H2-2023": [21, 33, 26, 12, 8],
    "H1-2024": [22, 33, 28, 10, 7],   # chart value. NB: H1-2024 prose headline says
    #                                   affordable "18%" & 45-90L "35%" — an ANAROCK
    #                                   chart-vs-text inconsistency; we use the chart.
    "H1-2025": [17, 25, 36, 12, 10],  # <- PRIMARY
}

# ---------------------------------------------------------------------------
# 3. BHK preference
# ---------------------------------------------------------------------------
BHK_TYPES = ["1BHK", "2BHK", "3BHK", "4BHK+"]

# Pan-India BHK distribution (%) per edition.
BHK_PAN_DIST = {
    "H1-2022": [11, 38, 44, 7],
    "H1-2023": [6,  39, 48, 7],
    "H2-2023": [4,  38, 50, 8],
    "H1-2024": [4,  39, 51, 6],
    "H1-2025": [8,  40, 45, 7],   # <- PRIMARY
}

# City-wise BHK distribution (%): {edition: {city: [1BHK,2BHK,3BHK,4BHK+]}}
# These are the persona-side preference priors per metro.
BHK_CITY_DIST = {
    "H1-2022": {
        "Bengaluru":  [7, 34, 51, 8],
        "Chennai":    [7, 40, 48, 5],
        "Delhi-NCR":  [9, 42, 45, 4],
        "Hyderabad":  [7, 49, 40, 4],
        "Kolkata":    [7, 47, 40, 6],
        "Mumbai-MMR": [21, 40, 37, 2],
        "Pune":       [11, 43, 40, 6],
        "Other":      [8, 22, 61, 9],
    },
    "H1-2023": {
        "Bengaluru":  [5, 36, 51, 8],
        "Chennai":    [6, 38, 50, 6],
        "Delhi-NCR":  [7, 40, 47, 6],
        "Hyderabad":  [6, 47, 45, 2],
        "Kolkata":    [6, 52, 37, 5],   # source prints 3BHK as "47%" (typo; labels sum 110). Width => 37%.
        "Mumbai-MMR": [23, 41, 34, 2],
        "Pune":       [10, 40, 45, 5],
        "Tier2_3":    [8, 19, 65, 8],
    },
    "H2-2023": {   # read from the horizontal-bar chart (inner ring = H2-2023)
        "Bengaluru":  [4, 39, 47, 10],
        "Chennai":    [5, 36, 53, 6],
        "Delhi-NCR":  [4, 36, 54, 6],
        "Hyderabad":  [4, 44, 48, 4],
        "Kolkata":    [5, 45, 47, 3],
        "Mumbai-MMR": [17, 44, 35, 4],
        "Pune":       [10, 40, 45, 5],
        "Other":      [6, 20, 67, 7],
    },
    "H1-2024": {   # all rows visually verified from the rendered chart
        "Bengaluru":  [5, 38, 50, 7],
        "Chennai":    [4, 34, 55, 6],
        "Delhi-NCR":  [5, 38, 52, 5],
        "Hyderabad":  [2, 39, 54, 5],
        "Kolkata":    [4, 46, 47, 3],
        "Mumbai-MMR": [19, 42, 35, 4],
        "Pune":       [11, 41, 46, 3],   # source labels sum to 101 (rounding)
        "Other":      [2, 26, 66, 6],
    },
    "H1-2025": {   # <- PRIMARY baseline (8 cities, incl. Ahmedabad)
        "Bengaluru":  [8, 34, 48, 10],
        "Chennai":    [6, 35, 53, 6],
        "Delhi-NCR":  [5, 36, 53, 6],
        "Hyderabad":  [2, 38, 55, 5],
        "Kolkata":    [4, 46, 46, 4],
        "Mumbai-MMR": [20, 40, 36, 4],
        "Pune":       [9, 41, 47, 3],
        "Ahmedabad":  [4, 29, 60, 7],
    },
}

# ---------------------------------------------------------------------------
# 4. Buyer intent: end-use vs investment (%)
# ---------------------------------------------------------------------------
INTENT_SERIES = {
    #            Pre  H1-20 H2-20 H1-21 H2-21 H1-22 H2-22 H1-23 H2-23 H1-24 H2-24 H1-25
    "end_use":    [67, 59,  74,   71,   68,   69,   71,   68,   64,   67,   63,   65],
    "investment": [33, 41,  26,   29,   32,   31,   29,   32,   36,   33,   37,   35],
}
INTENT_DIST = {
    "H1-2022": {"end_use": 69, "investment": 31},
    "H1-2023": {"end_use": 68, "investment": 32},
    "H2-2023": {"end_use": 64, "investment": 36},
    "H1-2024": {"end_use": 67, "investment": 33},
    "H1-2025": {"end_use": 65, "investment": 35},   # <- PRIMARY
}
# H1-2024 investor sub-intent (only edition that breaks it out):
#   earn rental income 57% / build asset for future 23% / sell on appreciation 20%

# ---------------------------------------------------------------------------
# 5. Best asset class for investment (%) — headline per edition
# ---------------------------------------------------------------------------
ASSET_CLASS_DIST = {
    # real_estate, stock_market, gold, fixed_deposit
    "H1-2022": {"real_estate": 59, "stock_market": 28, "gold": 7, "fixed_deposit": 6},
    "H1-2023": {"real_estate": 60, "stock_market": 27, "gold": 5, "fixed_deposit": 8},
    "H2-2023": {"real_estate": 57, "stock_market": 29, "gold": 6, "fixed_deposit": 8},
    "H1-2024": {"real_estate": 59, "stock_market": 30, "gold": 5, "fixed_deposit": 6},
    "H1-2025": {"real_estate": 63, "stock_market": 22, "gold": 7, "fixed_deposit": 8},
}

# ---------------------------------------------------------------------------
# 6. Preferred construction stage
# ---------------------------------------------------------------------------
# Headline "ready-to-move : new-launch" preference ratio per edition.
READY_TO_NEW_RATIO = {
    "H1-2020": (46, 18),
    "H1-2021": (32, 21),
    "H1-2022": (30, 25),
    "H1-2023": (28, 27),
    "H2-2023": (23, 24),
    "H1-2024": (20, 25),
    "H1-2025": (16, 29),   # <- PRIMARY: decisive tilt to new launches
}
# Full 4-way construction-stage preference (%) for the PRIMARY edition only.
CONSTRUCTION_STAGE_H1_2025 = {
    "new_launch": 29,
    "ready_to_move_in": 16,
    "ready_within_6_months": 30,
    "ready_within_1_year": 25,
}

# ---------------------------------------------------------------------------
# 7. Property side — zone-wise 2BHK budget range + average rate (INR/sqft)
#    THIS IS THE PERSONA <-> PROPERTY BRIDGE.
#    Structure: {edition: {city: {zone: {"bhk2_budget": (low, high), "rate_psf": int}}}}
#    "bhk2_budget" is the average all-in ticket range for a 2BHK in that zone.
#    Implied 2BHK carpet area ~= midpoint(bhk2_budget) / rate_psf  (sanity ~600-1100 sqft).
# ---------------------------------------------------------------------------
ZONE_TABLE = {
    # ============================== H1-2025 (PRIMARY) ======================
    "H1-2025": {
        "Mumbai-MMR": {
            "Mumbai Central Suburbs":     {"bhk2_budget": (160 * LAKH, 250 * LAKH), "rate_psf": 24950},
            "Mumbai Western Suburbs":     {"bhk2_budget": (180 * LAKH, 260 * LAKH), "rate_psf": 28000},
            "South Central Mumbai":       {"bhk2_budget": (330 * LAKH, 450 * LAKH), "rate_psf": 44000},
            "Peripheral Central Suburbs": {"bhk2_budget": (45 * LAKH,  65 * LAKH),  "rate_psf": 7750},
            "Peripheral Western Suburbs": {"bhk2_budget": (42 * LAKH,  58 * LAKH),  "rate_psf": 8000},
            "Navi Mumbai":                {"bhk2_budget": (90 * LAKH,  120 * LAKH), "rate_psf": 11200},
            "Thane":                      {"bhk2_budget": (95 * LAKH,  140 * LAKH), "rate_psf": 13700},
        },
        "Delhi-NCR": {
            "Gurgaon":       {"bhk2_budget": (90 * LAKH,  130 * LAKH), "rate_psf": 11000},
            "Noida":         {"bhk2_budget": (85 * LAKH,  120 * LAKH), "rate_psf": 9600},
            "Greater Noida": {"bhk2_budget": (40 * LAKH,  60 * LAKH),  "rate_psf": 6900},
            "Ghaziabad":     {"bhk2_budget": (45 * LAKH,  65 * LAKH),  "rate_psf": 5820},
            "Faridabad":     {"bhk2_budget": (42 * LAKH,  55 * LAKH),  "rate_psf": 4950},
        },
        "Bengaluru": {
            "Central Bengaluru": {"bhk2_budget": (150 * LAKH, 200 * LAKH), "rate_psf": 16650},
            "East Bengaluru":    {"bhk2_budget": (65 * LAKH,  100 * LAKH), "rate_psf": 8800},
            "North Bengaluru":   {"bhk2_budget": (60 * LAKH,  95 * LAKH),  "rate_psf": 8780},
            "South Bengaluru":   {"bhk2_budget": (55 * LAKH,  65 * LAKH),  "rate_psf": 7150},
            "West Bengaluru":    {"bhk2_budget": (55 * LAKH,  70 * LAKH),  "rate_psf": 8000},
        },
        "Pune": {
            "Central Pune": {"bhk2_budget": (130 * LAKH, 180 * LAKH), "rate_psf": 19800},
            "East Pune":    {"bhk2_budget": (58 * LAKH,  75 * LAKH),  "rate_psf": 7700},
            "North Pune":   {"bhk2_budget": (55 * LAKH,  70 * LAKH),  "rate_psf": 7000},
            "South Pune":   {"bhk2_budget": (60 * LAKH,  75 * LAKH),  "rate_psf": 7730},
            "West Pune":    {"bhk2_budget": (60 * LAKH,  75 * LAKH),  "rate_psf": 8970},
        },
        "Chennai": {
            "Central Chennai": {"bhk2_budget": (160 * LAKH, 200 * LAKH), "rate_psf": 20350},
            "North Chennai":   {"bhk2_budget": (50 * LAKH,  65 * LAKH),  "rate_psf": 6565},
            "South Chennai":   {"bhk2_budget": (55 * LAKH,  80 * LAKH),  "rate_psf": 6800},
            "West Chennai":    {"bhk2_budget": (60 * LAKH,  75 * LAKH),  "rate_psf": 7650},
        },
        "Kolkata": {
            "Kolkata Central": {"bhk2_budget": (90 * LAKH,  110 * LAKH), "rate_psf": 16700},
            "Kolkata East":    {"bhk2_budget": (40 * LAKH,  50 * LAKH),  "rate_psf": 5920},
            "Kolkata North":   {"bhk2_budget": (35 * LAKH,  45 * LAKH),  "rate_psf": 5030},
            "Kolkata South":   {"bhk2_budget": (40 * LAKH,  55 * LAKH),  "rate_psf": 5760},
            "Kolkata West":    {"bhk2_budget": (35 * LAKH,  45 * LAKH),  "rate_psf": 4850},
        },
        "Hyderabad": {
            "Central Hyderabad": {"bhk2_budget": (100 * LAKH, 150 * LAKH), "rate_psf": 10280},
            "East Hyderabad":    {"bhk2_budget": (55 * LAKH,  70 * LAKH),  "rate_psf": 6550},
            "North Hyderabad":   {"bhk2_budget": (55 * LAKH,  65 * LAKH),  "rate_psf": 6700},
            "South Hyderabad":   {"bhk2_budget": (45 * LAKH,  55 * LAKH),  "rate_psf": 6320},
            "West Hyderabad":    {"bhk2_budget": (65 * LAKH,  90 * LAKH),  "rate_psf": 8740},
        },
    },
}

# Historical ₹/sqft only (for price-escalation trend; budget ranges in EXTRACTED_DATA.md).
# {city: {zone: {edition: rate_psf}}}  — covers the editions in this repo.
ZONE_RATE_PSF_SERIES = {
    "Mumbai-MMR": {
        "Mumbai Central Suburbs": {"H1-2022": 18200, "H1-2023": 20100, "H2-2023": 22000, "H1-2024": 25500, "H1-2025": 24950},
        "Mumbai Western Suburbs": {"H1-2022": 20400, "H1-2023": 22200, "H2-2023": 24500, "H1-2024": 28000, "H1-2025": 28000},
        "South Central Mumbai":   {"H1-2022": 33300, "H1-2023": 35600, "H2-2023": 39000, "H1-2024": 44500, "H1-2025": 44000},
        "Navi Mumbai":            {"H1-2022": 7380,  "H1-2023": 8050,  "H2-2023": 8800,  "H1-2024": 10100, "H1-2025": 11200},
        "Thane":                  {"H1-2022": 9370,  "H1-2023": 10250, "H2-2023": 11200, "H1-2024": 12500, "H1-2025": 13700},
    },
    "Delhi-NCR": {
        "Gurgaon":       {"H1-2022": 6350, "H1-2023": 6900, "H2-2023": 7660, "H1-2024": 9000, "H1-2025": 11000},
        "Noida":         {"H1-2022": 5100, "H1-2023": 5550, "H2-2023": 6300, "H1-2024": 7600, "H1-2025": 9600},
        "Greater Noida": {"H1-2022": 3740, "H1-2023": 4100, "H2-2023": 4500, "H1-2024": 5300, "H1-2025": 6900},
    },
    "Bengaluru": {
        "Central Bengaluru": {"H1-2022": 10500, "H1-2023": 11750, "H2-2023": 12900, "H1-2024": 15200, "H1-2025": 16650},
        "East Bengaluru":    {"H1-2022": 5000,  "H1-2023": 5600,  "H2-2023": 6300,  "H1-2024": 7600,  "H1-2025": 8800},
    },
    "Pune": {
        "Central Pune": {"H1-2022": 14450, "H1-2023": 15700, "H2-2023": 17000, "H1-2024": 18400, "H1-2025": 19800},
    },
    "Chennai": {
        "Central Chennai": {"H1-2022": 15200, "H1-2023": 16350, "H2-2023": 17800, "H1-2024": 19000, "H1-2025": 20350},
    },
    "Kolkata": {
        "Kolkata Central": {"H1-2022": 12900, "H1-2023": 13700, "H2-2023": 14500, "H1-2024": 15400, "H1-2025": 16700},
    },
    "Hyderabad": {
        "Central Hyderabad": {"H1-2022": 6400, "H1-2023": 7100, "H2-2023": 8000, "H1-2024": 9450, "H1-2025": 10280},
    },
}

# ---------------------------------------------------------------------------
# 8. Modeling constants for the affordability coupling (the methodological core)
# ---------------------------------------------------------------------------
# Ticket size ~= AFFORDABILITY_MULTIPLE * annual household income, then gated
# by zone rate_psf * carpet area and clipped to the buyer's stated budget band.
AFFORDABILITY_MULTIPLE = (4.0, 5.0)   # ticket / annual income, defensible band

# Typical carpet area by BHK (sqft) for backing out ticket size from rate_psf.
# Used when a property's ticket must be derived for a non-2BHK unit.
BHK_CARPET_SQFT = {
    "1BHK":  (400, 650),
    "2BHK":  (650, 1100),
    "3BHK":  (1000, 1600),
    "4BHK+": (1600, 2800),
}

# Average flat size across top-7 cities (sqft) — trend context (H1-2024 report).
AVG_FLAT_SIZE_SQFT = {2019: 1145, 2020: 1167, 2021: 1170, 2022: 1175, 2023: 1300, "H1-2024": 1513}

# Home-loan rate sensitivity (H1-2025 still implicit; clearest in H1-2024/H2-2023):
# share reporting HIGH impact on buying decision at each rate band.
LOAN_RATE_HIGH_IMPACT = {  # edition H1-2024
    "<8.5%": 12, "8.5-9%": 35, "9-9.5%": 87, ">9.5%": 94,
}

# Cities that have BHK preference data but NO zone ₹/sqft table in H1-2025.
CITIES_WITHOUT_ZONE_TABLE = ["Ahmedabad"]


def _check_distributions():
    """Quick check that every marginal adds up to around 100."""
    issues = []
    for ed, d in INCOME_DIST.items():
        if abs(sum(d) - 100) > 1:
            issues.append(f"INCOME_DIST[{ed}] sums to {sum(d)}")
    for ed, d in BUDGET_DIST.items():
        if abs(sum(d) - 100) > 1:
            issues.append(f"BUDGET_DIST[{ed}] sums to {sum(d)}")
    for ed, d in BHK_PAN_DIST.items():
        if abs(sum(d) - 100) > 1:
            issues.append(f"BHK_PAN_DIST[{ed}] sums to {sum(d)}")
    for ed, cities in BHK_CITY_DIST.items():
        for city, d in cities.items():
            if abs(sum(d) - 100) > 2:
                issues.append(f"BHK_CITY_DIST[{ed}][{city}] sums to {sum(d)}")
    return issues


if __name__ == "__main__":
    probs = _check_distributions()
    if probs:
        print("Distribution sanity warnings:")
        for p in probs:
            print("  -", p)
    else:
        print("All marginal distributions sum to ~100. OK.")
    print(f"\nPRIMARY edition: H1-2025  ({SURVEY_META['H1-2025']['respondents']} respondents)")
    n_zones = sum(len(z) for z in ZONE_TABLE['H1-2025'].values())
    print(f"H1-2025 zone table: {len(ZONE_TABLE['H1-2025'])} cities, {n_zones} zones")
