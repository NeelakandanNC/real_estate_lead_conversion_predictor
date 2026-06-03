"""
Trains one clean LightGBM (+ isotonic calibration) just for serving, then exports
it to ONNX so the website can score leads without any Python. The CalibratedClassifierCV
we use in modelling.py averages 3 boosters which is messy to ship, so here we keep a
single booster and write the calibration curve out to meta.json instead. The JS backend
loads the .onnx for the raw score and applies that little curve on top.
"""

import json
import numpy as np
import pandas as pd

from lightgbm import LGBMClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, brier_score_loss
from onnxmltools.convert import convert_lightgbm
from onnxmltools.convert.common.data_types import FloatTensorType
import onnxruntime as ort

import priors
from preprocessing import add_engineered, ENCODED_CSV, SEED
from modelling import FEATURES

ONNX_OUT = "../web/model/lead_scorer.onnx"
META_OUT = "../web/model/meta.json"


def main():
    df = add_engineered(pd.read_csv(ENCODED_CSV))
    X, y = df[FEATURES].astype("float32"), df["converted"].values

    # train / calibration / test
    X_tmp, X_te, y_tmp, y_te = train_test_split(X, y, test_size=0.30,
                                                stratify=y, random_state=SEED)
    X_fit, X_cal, y_fit, y_cal = train_test_split(X_tmp, y_tmp, test_size=0.25,
                                                  stratify=y_tmp, random_state=SEED)
    spw = (y_fit == 0).sum() / (y_fit == 1).sum()

    model = LGBMClassifier(n_estimators=400, learning_rate=0.03, num_leaves=31,
                           subsample=0.8, colsample_bytree=0.8, scale_pos_weight=spw,
                           random_state=SEED, n_jobs=-1, verbose=-1)
    model.fit(X_fit, y_fit)

    # isotonic calibration on the held-out slice
    raw_cal = model.predict_proba(X_cal)[:, 1]
    iso = IsotonicRegression(out_of_bounds="clip").fit(raw_cal, y_cal)

    raw_te = model.predict_proba(X_te)[:, 1]
    cal_te = iso.predict(raw_te)
    print(f"served model: ROC-AUC={roc_auc_score(y_te, raw_te):.3f}  "
          f"Brier(raw)={brier_score_loss(y_te, raw_te):.4f}  "
          f"Brier(cal)={brier_score_loss(y_te, cal_te):.4f}")

    # --- LightGBM -> ONNX ---
    onx = convert_lightgbm(
        model, initial_types=[("input", FloatTensorType([None, len(FEATURES)]))],
        zipmap=False, target_opset=13)
    with open(ONNX_OUT, "wb") as f:
        f.write(onx.SerializeToString())

    # sanity: onnxruntime output must match sklearn's raw probability
    sess = ort.InferenceSession(ONNX_OUT, providers=["CPUExecutionProvider"])
    onnx_p = sess.run(None, {"input": X_te.values[:200]})[1][:, 1]
    max_diff = float(np.abs(onnx_p - raw_te[:200]).max())
    print(f"ONNX vs sklearn max prob diff = {max_diff:.2e}  ({'OK' if max_diff < 1e-5 else 'CHECK'})")

    # --- meta.json: everything the JS side needs to reproduce a score ---
    meta = {
        "features": FEATURES,
        "base_rate": round(float(y.mean()), 4),
        "budget_bands_inr": [[int(lo), int(hi)] for _, (lo, hi) in priors.BUDGET_BANDS],
        "bhk_order": priors.BHK_TYPES,
        "calibration_isotonic": {
            "x": [round(float(v), 6) for v in iso.X_thresholds_],
            "y": [round(float(v), 6) for v in iso.y_thresholds_],
        },
        "metrics": {"roc_auc": round(float(roc_auc_score(y_te, raw_te)), 3)},
        "note": "raw P = onnx(input)[:,1]; final P = piecewise-linear interp of (x,y).",
    }
    with open(META_OUT, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"wrote {ONNX_OUT} and {META_OUT}")


if __name__ == "__main__":
    main()
