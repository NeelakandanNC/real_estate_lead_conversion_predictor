"""
Turns the raw leads_synthetic.csv into model-ready numbers and then works out
which columns actually carry signal. Encoding drops `zone` (its price is already
in rate_psf), makes intent a 0/1 flag, maps the BHK columns to 1-4 since they
have a natural order, and one-hots the 7 cities. After that we add a couple of
simple engineered features and rank everything with mutual information and
correlation, so we know what to feed the model.
"""

import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_classif

RAW_CSV = "leads_synthetic.csv"
ENCODED_CSV = "leads_encoded.csv"
RANK_CSV = "feature_ranking.csv"

BHK_ORDER = {"1BHK": 1, "2BHK": 2, "3BHK": 3, "4BHK+": 4}   # ordinal
INTENT_MAP = {"end_use": 0, "investment": 1}                 # binary flag
MI_SAMPLE = 50_000          # subsample just to keep MI fast
SEED = 42


# --------------------------------------------------------------------------- #
# encoding
# --------------------------------------------------------------------------- #
def encode(df):
    df = df.drop(columns=["zone"])                              # 1) drop zone
    df["intent"] = df["intent"].map(INTENT_MAP).astype(int)     # 2) intent -> 0/1
    for col in ["bhk_preference", "bhk_enquired"]:              # 3) bhk -> 1..4
        df[col] = df[col].map(BHK_ORDER).astype(int)
    df = pd.get_dummies(df, columns=["city"], prefix="city")    # 4) city one-hot
    city_cols = [c for c in df.columns if c.startswith("city_")]
    df[city_cols] = df[city_cols].astype(int)
    return df


def add_engineered(df):
    # how far the flat sits vs what they said they'd spend (>1 = over budget)
    df["price_to_budget"] = df["property_ticket"] / df["stated_budget"]
    # did they enquire bigger/smaller than their preferred BHK
    df["bhk_delta"] = df["bhk_enquired"] - df["bhk_preference"]
    return df


# --------------------------------------------------------------------------- #
# feature relevance (mutual information + correlation)
# --------------------------------------------------------------------------- #
def analyze_features(df):
    y = df["converted"].values
    X = df.drop(columns=["converted", "_true_p"])    # _true_p is the oracle, not a feature
    feats = list(X.columns)
    print(f"{len(df):,} rows, {len(feats)} candidate features, base rate {y.mean()*100:.2f}%")

    discrete = [c for c in feats if X[c].dropna().nunique() <= 6 or c.startswith("city_")
                or c in ("intent", "budget_match", "bhk_match",
                         "bhk_preference", "bhk_enquired", "bhk_delta")]
    disc_mask = [c in discrete for c in feats]

    rng = np.random.default_rng(SEED)
    idx = rng.choice(len(df), size=min(MI_SAMPLE, len(df)), replace=False)
    mi = mutual_info_classif(X.iloc[idx], y[idx], discrete_features=disc_mask,
                             random_state=SEED)
    corr = np.array([abs(np.corrcoef(X[c].values, y)[0, 1]) for c in feats])

    rank = (pd.DataFrame({"feature": feats, "mutual_info": mi, "abs_corr": corr})
            .sort_values("mutual_info", ascending=False).reset_index(drop=True))
    pd.set_option("display.float_format", lambda v: f"{v:.4f}")
    print("\n=== feature relevance (sorted by mutual information) ===")
    print(rank.to_string(index=True))

    # redundancy: feature pairs that are basically the same column
    cmat = X.corr(numeric_only=True).abs()
    cols, pairs = cmat.columns, []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            if cmat.iloc[i, j] >= 0.90:
                pairs.append((cols[i], cols[j], cmat.iloc[i, j]))
    print("\n=== near-duplicate feature pairs (|corr| >= 0.90) ===")
    for a, b, c in sorted(pairs, key=lambda t: -t[2]) or [("none", "", 0)]:
        print(f"  {a:<22} ~ {b:<22} {c:.3f}" if b else "  none")

    rank.to_csv(RANK_CSV, index=False)
    print(f"\nwrote {RANK_CSV}")
    return rank


def main():
    df = encode(pd.read_csv(RAW_CSV))
    df.to_csv(ENCODED_CSV, index=False)
    print(f"wrote {ENCODED_CSV}: {len(df):,} rows x {df.shape[1]} cols\n")
    df = add_engineered(df)
    analyze_features(df)


if __name__ == "__main__":
    main()
