"""
Exports the model the *website* uses: the LightGBM trees + the isotonic calibration,
dumped to one small JSON. A gradient-boosted model is just tree lookups + a sum, so the
site can score leads in plain JavaScript with no ML runtime at all (that's what kept the
onnxruntime build under Vercel's 250 MB limit). We train with boost_from_average=False so
the raw score is exactly the sum of leaf values, and we calibrate straight off that raw
score - so the JS side only has to: walk trees -> sum -> interpolate the calibration curve.
Also writes selftest_predictions.json so the Node side can prove it matches Python.
"""

import json
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, brier_score_loss

import priors
from preprocessing import add_engineered, ENCODED_CSV, SEED

FEATURES = ["affordability_ratio", "annual_income", "price_to_budget",
            "budget_match", "bhk_match", "intent"]
MODEL_OUT = "../web/model/model.json"
SELFTEST_OUT = "selftest_predictions.json"


def compact(node):
    """LightGBM tree node -> tiny {f,t,l,r} (internal) or {v} (leaf)."""
    if "split_feature" not in node:           # leaf
        return {"v": float(node["leaf_value"])}
    assert node["decision_type"] == "<=", "only <= splits expected"
    return {"f": int(node["split_feature"]), "t": float(node["threshold"]),
            "l": compact(node["left_child"]), "r": compact(node["right_child"])}


def main():
    df = add_engineered(pd.read_csv(ENCODED_CSV))
    X, y = df[FEATURES].astype("float64"), df["converted"].values

    X_tmp, X_te, y_tmp, y_te = train_test_split(X, y, test_size=0.30,
                                                stratify=y, random_state=SEED)
    X_fit, X_cal, y_fit, y_cal = train_test_split(X_tmp, y_tmp, test_size=0.25,
                                                  stratify=y_tmp, random_state=SEED)
    spw = (y_fit == 0).sum() / (y_fit == 1).sum()

    model = LGBMClassifier(n_estimators=400, learning_rate=0.03, num_leaves=31,
                           subsample=0.8, colsample_bytree=0.8, scale_pos_weight=spw,
                           boost_from_average=False, random_state=SEED,
                           n_jobs=-1, verbose=-1)
    model.fit(X_fit, y_fit)
    booster = model.booster_

    # calibrate directly on the raw margin (= sum of leaf values)
    raw_cal = booster.predict(X_cal, raw_score=True)
    iso = IsotonicRegression(out_of_bounds="clip").fit(raw_cal, y_cal)
    raw_te = booster.predict(X_te, raw_score=True)
    p_te = iso.predict(raw_te)
    print(f"served model: ROC-AUC={roc_auc_score(y_te, raw_te):.3f}  "
          f"Brier(cal)={brier_score_loss(y_te, p_te):.4f}  trees={booster.num_trees()}")

    dump = booster.dump_model()
    model_json = {
        "features": FEATURES,
        "base_rate": round(float(y.mean()), 4),
        "budget_bands_inr": [[int(lo), int(hi)] for _, (lo, hi) in priors.BUDGET_BANDS],
        "bhk_order": priors.BHK_TYPES,
        "calibration": {
            "x": [float(v) for v in iso.X_thresholds_],
            "y": [float(v) for v in iso.y_thresholds_],
        },
        "trees": [compact(t["tree_structure"]) for t in dump["tree_info"]],
    }
    with open(MODEL_OUT, "w") as f:
        json.dump(model_json, f)
    import os
    print(f"wrote {MODEL_OUT}  ({os.path.getsize(MODEL_OUT)/1e6:.2f} MB, "
          f"{len(model_json['trees'])} trees)")

    # selftest: feature rows + the python probability, so Node can prove a match
    rows = X_te.values[:200]
    p_rows = iso.predict(booster.predict(rows, raw_score=True))
    json.dump([{"x": [float(v) for v in r], "p": float(p)}
               for r, p in zip(rows, p_rows)], open(SELFTEST_OUT, "w"))
    print(f"wrote {SELFTEST_OUT} (200 rows for the JS parity check)")


if __name__ == "__main__":
    main()
