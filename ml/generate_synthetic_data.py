"""
Builds a fake real-estate calling list that lines up with the ANAROCK survey
numbers, so we actually have something to train a lead-scoring model on. We make
the person first - income, city, the flat they're asking about - and tie the price
back to income with the 4-5x affordability rule, then hand each row a `converted`
label that works out to roughly 1.5% buyers. The label leans only on persona and
affordability stuff (no site-visit / engagement signals), so the model is partly
re-learning our own rules - thats fine for a demo, drop in a real CRM later and it
stops being circular. Output is leads_synthetic.csv, where `converted` is the label
to train on and `_true_p` is just the true probability we kept for the plots.
"""

from __future__ import annotations
import numpy as np
import pandas as pd

import priors

# --------------------------------------------------------------------------- #
# Config (locked per project decision)
# --------------------------------------------------------------------------- #
SEED = 42
N = 200_000
TARGET_BASE_RATE = 0.015          # ~1.5% conversions
EDITION = "H1-2025"               # primary baseline
NOISE_SIGMA = 1.35                # irreducible randomness -> targets AUC ~0.80
OUT_CSV = "leads_synthetic.csv"

# H1-2025 new-home supply per metro (zone tables) -> proxy for market activity /
# inbound call volume. Ahmedabad is excluded: it has BHK data but NO zone table.
CITY_SUPPLY = {
    "Mumbai-MMR": 58_900, "Bengaluru": 36_200, "Pune": 31_100,
    "Delhi-NCR": 29_900, "Hyderabad": 21_400, "Chennai": 13_300, "Kolkata": 7_900,
}

# Loan assumptions for the EMI-burden feature.
HOME_LOAN_RATE_ANNUAL = 0.086     # ~8.6% (survey-era home-loan rate)
LOAN_TENURE_YEARS = 20

rng = np.random.default_rng(SEED)


# --------------------------------------------------------------------------- #
# Small sampling helpers
# --------------------------------------------------------------------------- #
def _norm(p):
    p = np.asarray(p, float)
    return p / p.sum()


def sample_categorical(categories, weights, size):
    """Draw `size` labels from the categories using the given weights."""
    idx = rng.choice(len(categories), size=size, p=_norm(weights))
    return np.asarray(categories)[idx]


def sample_within_band(bands, band_idx):
    """Pick an actual value inside each chosen band. The open-ended top band gets
    an exponential tail above its lower edge so a few rows go really high."""
    los = np.array([b[1][0] for b in bands], float)
    his = np.array([b[1][1] for b in bands], float)
    lo = los[band_idx]
    hi = his[band_idx]
    vals = rng.uniform(lo, hi)
    # top band = open-ended: replace uniform with lo + exponential tail (capped)
    top = band_idx == (len(bands) - 1)
    n_top = int(top.sum())
    if n_top:
        tail = lo[top] + rng.exponential((hi[top] - lo[top]) * 0.8, size=n_top)
        vals[top] = np.minimum(tail, hi[top] * 1.6)
    return vals


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))


def carpet_for_bhk(bhk_array):
    """Give each row a carpet area in sqft, based on its BHK size."""
    out = np.empty(len(bhk_array), float)
    for bhk, (lo, hi) in priors.BHK_CARPET_SQFT.items():
        m = bhk_array == bhk
        if m.any():
            out[m] = rng.uniform(lo, hi, size=int(m.sum()))
    return out


def bhk_mid_carpet():
    return {b: (lo + hi) / 2 for b, (lo, hi) in priors.BHK_CARPET_SQFT.items()}


# --------------------------------------------------------------------------- #
# Job 1 - generate the feature rows (persona-first)
# --------------------------------------------------------------------------- #
def generate_features(n):
    bhk_types = priors.BHK_TYPES
    mid_carpet = bhk_mid_carpet()

    # --- persona attributes (from marginals) ---
    city = sample_categorical(list(CITY_SUPPLY), list(CITY_SUPPLY.values()), n)

    inc_band = rng.choice(len(priors.INCOME_BANDS), size=n,
                          p=_norm(priors.INCOME_DIST[EDITION]))
    income = sample_within_band(priors.INCOME_BANDS, inc_band)          # INR / yr

    age = np.clip(np.round(rng.triangular(24, 36, 78, size=n)), 24, 78).astype(int)

    intent_inv = priors.INTENT_DIST[EDITION]["investment"] / 100.0
    intent = np.where(rng.random(n) < intent_inv, "investment", "end_use")

    bud_band = rng.choice(len(priors.BUDGET_BANDS), size=n,
                          p=_norm(priors.BUDGET_DIST[EDITION]))
    budget_value = sample_within_band(priors.BUDGET_BANDS, bud_band)    # stated budget

    # BHK *preference* depends on city (city-wise distributions)
    bhk_pref = np.empty(n, dtype=object)
    for c in CITY_SUPPLY:
        m = city == c
        if m.any():
            bhk_pref[m] = sample_categorical(
                bhk_types, priors.BHK_CITY_DIST[EDITION][c], int(m.sum()))

    # enquired BHK = preference, but ~22% enquire about an adjacent size
    shift = rng.random(n)
    pref_idx = np.array([bhk_types.index(b) for b in bhk_pref])
    enq_idx = pref_idx.copy()
    up = (shift > 0.88) & (pref_idx < 3)
    dn = (shift < 0.12) & (pref_idx > 0)
    enq_idx[up] += 1
    enq_idx[dn] -= 1
    bhk_enquired = np.asarray(bhk_types)[enq_idx]

    # --- the COUPLING: pick the zone they enquire about -------------------- #
    # affordable ticket anchor = income x U(4,5)
    afford_ticket = income * rng.uniform(*priors.AFFORDABILITY_MULTIPLE, size=n)

    rate_psf = np.empty(n, float)
    zone_name = np.empty(n, dtype=object)
    zt = priors.ZONE_TABLE[EDITION]
    TAU = 0.45  # softmax temperature on log-ticket distance (smaller = pickier)
    for c in CITY_SUPPLY:
        m = np.where(city == c)[0]
        if len(m) == 0:
            continue
        zones = list(zt[c].items())                       # [(zname, {...}), ...]
        zrates = np.array([z[1]["rate_psf"] for z in zones], float)
        # representative ticket of each zone for THIS lead's enquired BHK
        carp_mid = np.array([mid_carpet[b] for b in bhk_enquired[m]])  # (len(m),)
        zticket = zrates[None, :] * carp_mid[:, None]                  # (len(m), Z)
        dist = np.abs(np.log(zticket) - np.log(afford_ticket[m])[:, None])
        w = _row_softmax(-dist / TAU)
        pick = _row_choice(w)
        rate_psf[m] = zrates[pick]
        zone_name[m] = np.asarray([z[0] for z in zones])[pick]

    # actual property ticket = rate/sqft x sampled carpet area
    carpet = carpet_for_bhk(bhk_enquired)
    property_ticket = rate_psf * carpet

    # --- financing / EMI --------------------------------------------------- #
    downpayment_pct = rng.uniform(0.15, 0.30, size=n)
    loan_amt = property_ticket * (1 - downpayment_pct)
    r = HOME_LOAN_RATE_ANNUAL / 12
    nper = LOAN_TENURE_YEARS * 12
    emi = loan_amt * r * (1 + r) ** nper / ((1 + r) ** nper - 1)
    emi_to_income = emi / (income / 12.0)                  # monthly EMI / monthly income

    # --- derived FIT features --------------------------------------------- #
    affordability_ratio = property_ticket / income
    bud_lo = np.array([b[1][0] for b in priors.BUDGET_BANDS])[bud_band]
    bud_hi = np.array([b[1][1] for b in priors.BUDGET_BANDS])[bud_band]
    budget_match = ((property_ticket >= bud_lo) & (property_ticket <= bud_hi)).astype(int)
    bhk_match = (bhk_enquired == bhk_pref).astype(int)

    return pd.DataFrame({
        "city": city,
        "zone": zone_name,
        "age": age,
        "annual_income": np.round(income).astype(int),
        "intent": intent,
        "bhk_preference": bhk_pref,
        "bhk_enquired": bhk_enquired,
        "stated_budget": np.round(budget_value).astype(int),
        "rate_psf": np.round(rate_psf).astype(int),
        "carpet_sqft": np.round(carpet).astype(int),
        "property_ticket": np.round(property_ticket).astype(int),
        "downpayment_pct": np.round(downpayment_pct, 3),
        "loan_amount": np.round(loan_amt).astype(int),
        "emi_monthly": np.round(emi).astype(int),
        "emi_to_income": np.round(emi_to_income, 3),
        "affordability_ratio": np.round(affordability_ratio, 2),
        "budget_match": budget_match,
        "bhk_match": bhk_match,
    })


def _row_softmax(a):
    a = a - a.max(axis=1, keepdims=True)
    e = np.exp(a)
    return e / e.sum(axis=1, keepdims=True)


def _row_choice(probs):
    """Pick one column per row, each row using its own probabilites."""
    c = np.cumsum(probs, axis=1)
    u = rng.random(len(probs))[:, None]
    return (u > c).sum(axis=1).clip(0, probs.shape[1] - 1)


# --------------------------------------------------------------------------- #
# Job 2 - generate the conversion label
# --------------------------------------------------------------------------- #
def attach_label(df):
    # affordability_fit: ~1 when the ticket is comfortably affordable, falls off
    # once it exceeds ~5.5x income (over-reach => won't convert).
    affordability_fit = sigmoid((5.5 - df["affordability_ratio"].values) * 1.4)
    emi_excess = np.maximum(0.0, df["emi_to_income"].values - 0.45)   # >45% burden hurts
    end_use = (df["intent"].values == "end_use").astype(float)

    # latent score (weights are interpretable, not learned)
    z0 = (
        2.30 * affordability_fit
        + 0.80 * df["budget_match"].values
        + 0.45 * df["bhk_match"].values
        + 0.30 * end_use
        - 1.80 * emi_excess
    )
    noise = rng.normal(0.0, NOISE_SIGMA, size=len(df))
    z0 = z0 + noise

    # calibrate intercept b0 so mean(p) == TARGET_BASE_RATE (bisection)
    b0 = _calibrate_intercept(z0, TARGET_BASE_RATE)
    p = sigmoid(b0 + z0)
    converted = (rng.random(len(df)) < p).astype(int)

    df = df.copy()
    df["_true_p"] = np.round(p, 5)          # oracle only (drop for real data)
    df["converted"] = converted
    return df, b0


def _calibrate_intercept(z0, target, lo=-20.0, hi=20.0, iters=60):
    for _ in range(iters):
        mid = (lo + hi) / 2
        if sigmoid(mid + z0).mean() < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# --------------------------------------------------------------------------- #
# Optional self-check: can a simple model recover the ranking? (lift/AUC)
# --------------------------------------------------------------------------- #
def quick_eval(df):
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import roc_auc_score
        from sklearn.model_selection import train_test_split
    except ImportError:
        print("  (sklearn not installed - skipping AUC/lift self-check)")
        return

    feat = pd.get_dummies(
        df[["city", "intent", "bhk_preference", "bhk_enquired", "age",
            "annual_income", "property_ticket", "emi_to_income",
            "affordability_ratio", "budget_match", "bhk_match"]],
        columns=["city", "intent", "bhk_preference", "bhk_enquired"],
    )
    y = df["converted"].values
    Xtr, Xte, ytr, yte = train_test_split(feat, y, test_size=0.3,
                                          stratify=y, random_state=SEED)
    clf = LogisticRegression(max_iter=2000, class_weight="balanced")
    clf.fit(Xtr, ytr)
    proba = clf.predict_proba(Xte)[:, 1]
    auc = roc_auc_score(yte, proba)

    # top-decile lift / cumulative gains
    order = np.argsort(-proba)
    yte_sorted = yte[order]
    base = yte.mean()
    top10 = yte_sorted[: max(1, len(yte) // 10)].mean()
    top20_capture = yte_sorted[: max(1, len(yte) // 5)].sum() / yte.sum()
    print(f"  logistic AUC (held-out)      : {auc:.3f}")
    print(f"  top-decile lift              : {top10 / base:.2f}x  (decile {top10*100:.1f}% vs base {base*100:.2f}%)")
    print(f"  buyers captured in top 20%   : {top20_capture*100:.1f}%")


# --------------------------------------------------------------------------- #
def main():
    print(f"Generating {N:,} synthetic leads (edition={EDITION}, seed={SEED}) ...")
    df = generate_features(N)
    df, b0 = attach_label(df)

    rate = df["converted"].mean()
    print(f"\nDone. base conversion rate = {rate*100:.2f}%  "
          f"({df['converted'].sum():,} buyers)   intercept b0={b0:.2f}")
    print("\nFeature snapshot:")
    print(df[["city", "annual_income", "bhk_enquired", "property_ticket",
              "affordability_ratio", "emi_to_income", "budget_match",
              "bhk_match", "converted"]].head(8).to_string(index=False))

    print("\nConversion rate by affordability_ratio bucket (sanity):")
    buckets = pd.cut(df["affordability_ratio"], [0, 3, 4, 5, 6, 8, 100])
    print((df.groupby(buckets, observed=True)["converted"].mean() * 100)
          .round(2).to_string())

    print("\nSelf-check (does a simple model recover the ranking?):")
    quick_eval(df)

    df.to_csv(OUT_CSV, index=False)
    print(f"\nWrote {OUT_CSV}  ({len(df):,} rows x {df.shape[1]} cols)")


if __name__ == "__main__":
    main()
