"""
Trains the lead-scoring model on the lean feature set and checks how well it
ranks buyers. We use LightGBM (gradient boosting, since the signal is nonlinear),
fix the 1.5% imbalance with scale_pos_weight, then calibrate the probabilities so
P(buy) means what it says. The headline output is the lift / cumulative-gains
curve - "call the top X% of the list, reach Y% of the buyers".
"""

import os
import pickle
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
from sklearn.metrics import (roc_auc_score, average_precision_score,
                             brier_score_loss, roc_curve)

from preprocessing import add_engineered, ENCODED_CSV, SEED

warnings.filterwarnings("ignore")

FEATURES = ["affordability_ratio", "annual_income", "price_to_budget",
            "budget_match", "bhk_match", "intent"]
FIGS = "figs"
MODEL_PKL = "lead_scorer.pkl"


def load_xy():
    df = add_engineered(pd.read_csv(ENCODED_CSV))
    return df[FEATURES].copy(), df["converted"].values


def lift_table(y_true, scores, n_bins=10):
    """Sort leads by score, then show how many buyers sit in each decile."""
    order = np.argsort(-scores)
    y_sorted = y_true[order]
    base, n, total = y_true.mean(), len(y_true), y_true.sum()
    rows = []
    for d in range(1, n_bins + 1):
        k = int(n * d / n_bins)
        captured = y_sorted[:k].sum()
        rows.append({
            "top_%": d * 100 // n_bins,
            "decile_rate_%": round(y_sorted[int(n*(d-1)/n_bins):k].mean() * 100, 2),
            "buyers_captured_%": round(captured / total * 100, 1),
            "lift": round((captured / k) / base, 2),
        })
    return pd.DataFrame(rows)


def main():
    os.makedirs(FIGS, exist_ok=True)
    X, y = load_xy()
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.30,
                                          stratify=y, random_state=SEED)
    spw = (ytr == 0).sum() / (ytr == 1).sum()        # ~65, fixes the imbalance
    print(f"train {len(Xtr):,} / test {len(Xte):,}  base rate {y.mean()*100:.2f}%  "
          f"scale_pos_weight={spw:.1f}")

    base_model = LGBMClassifier(
        n_estimators=400, learning_rate=0.03, num_leaves=31,
        subsample=0.8, colsample_bytree=0.8, scale_pos_weight=spw,
        random_state=SEED, n_jobs=-1, verbose=-1,
    )
    # calibrate probabilities (isotonic, internal CV) so P(buy) is trustworthy
    model = CalibratedClassifierCV(base_model, method="isotonic", cv=3)
    model.fit(Xtr, ytr)

    proba = model.predict_proba(Xte)[:, 1]
    auc = roc_auc_score(yte, proba)
    ap = average_precision_score(yte, proba)
    brier = brier_score_loss(yte, proba)
    print(f"\nROC-AUC = {auc:.3f}   PR-AUC = {ap:.3f}   Brier = {brier:.4f}")

    lt = lift_table(yte, proba)
    print("\n=== cumulative gains / lift (test set) ===")
    print(lt.to_string(index=False))
    top20 = lt.loc[lt['top_%'] == 20, 'buyers_captured_%'].iloc[0]
    print(f"\nHeadline: calling the top 20% of the list reaches {top20}% of all buyers.")

    importances = np.mean([est.estimator.feature_importances_
                           for est in model.calibrated_classifiers_], axis=0)
    imp = (pd.DataFrame({"feature": FEATURES, "importance": importances})
           .sort_values("importance", ascending=False))
    print("\n=== feature importance (LightGBM gain) ===")
    print(imp.to_string(index=False))

    _plots(yte, proba, imp)
    print(f"\nsaved plots to {FIGS}/  (gains_curve.png, roc.png, calibration.png, importance.png)")

    # persist the fitted model + the feature order it expects, so scoring a new
    # calling list later is just: load pickle -> predict_proba on these columns.
    with open(MODEL_PKL, "wb") as f:
        pickle.dump({"model": model, "features": FEATURES,
                     "metrics": {"roc_auc": auc, "pr_auc": ap, "brier": brier}}, f)
    print(f"saved model to {MODEL_PKL}")


def _plots(yte, proba, imp):
    # cumulative gains
    order = np.argsort(-proba); ys = yte[order]
    pct = np.arange(1, len(ys) + 1) / len(ys) * 100
    gains = np.cumsum(ys) / ys.sum() * 100
    plt.figure(figsize=(6, 5))
    plt.plot(pct, gains, label="model")
    plt.plot([0, 100], [0, 100], "--", color="grey", label="random")
    plt.xlabel("% of list called (ranked by score)")
    plt.ylabel("% of buyers reached")
    plt.title("Cumulative gains"); plt.legend(); plt.grid(alpha=.3); plt.tight_layout()
    plt.savefig(f"{FIGS}/gains_curve.png", dpi=130); plt.close()

    # roc
    fpr, tpr, _ = roc_curve(yte, proba)
    plt.figure(figsize=(6, 5))
    plt.plot(fpr, tpr); plt.plot([0, 1], [0, 1], "--", color="grey")
    plt.xlabel("FPR"); plt.ylabel("TPR"); plt.title("ROC curve")
    plt.grid(alpha=.3); plt.tight_layout()
    plt.savefig(f"{FIGS}/roc.png", dpi=130); plt.close()

    # calibration
    bins = np.linspace(0, proba.max(), 11)
    idx = np.digitize(proba, bins) - 1
    xs, obs = [], []
    for b in range(len(bins) - 1):
        m = idx == b
        if m.sum() > 30:
            xs.append(proba[m].mean()); obs.append(yte[m].mean())
    plt.figure(figsize=(6, 5))
    plt.plot(xs, obs, "o-", label="model")
    plt.plot([0, max(xs)], [0, max(xs)], "--", color="grey")
    plt.xlabel("predicted P(buy)"); plt.ylabel("observed buy rate")
    plt.title("Calibration"); plt.legend(); plt.grid(alpha=.3); plt.tight_layout()
    plt.savefig(f"{FIGS}/calibration.png", dpi=130); plt.close()

    # importance
    plt.figure(figsize=(6, 4))
    plt.barh(imp["feature"][::-1], imp["importance"][::-1])
    plt.title("Feature importance (gain)"); plt.tight_layout()
    plt.savefig(f"{FIGS}/importance.png", dpi=130); plt.close()


if __name__ == "__main__":
    main()
