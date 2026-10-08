"""Compute the evaluation numbers shown in the app from the saved models and the hold-out test split.

Run from the final_system folder after stage7_tuning.py:   python scripts/build_metrics.py

Output: data/model_metrics.json
  - per-model test R2 / RMSE / MAE
  - for the final model: the range of (actual / predicted) covering 80% of test vehicles,
    used by the app to show an estimated price range.
"""
import json
import os
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "data", "tuning_results.json")) as f:
    tuning = json.load(f)

test = pd.read_csv(os.path.join(ROOT, "data", "test_processed.csv"))
features = [c for c in test.columns if not c.startswith("Target_")]
X, y = test[features], test["Target_Price"].to_numpy()

metrics = {"champion": tuning["champion"], "selection_rule": tuning["selection_rule"], "models": {}}
for key in tuning["models"]:
    model = joblib.load(os.path.join(ROOT, "models", f"{key}.joblib"))
    pred = np.clip(model.predict(X), 500, 150000)
    metrics["models"][key] = {
        "test_r2": round(float(r2_score(y, pred)), 4),
        "test_rmse": round(float(np.sqrt(mean_squared_error(y, pred))), 2),
        "test_mae": round(float(mean_absolute_error(y, pred)), 2),
        "cv_r2": round(tuning["models"][key]["tuned"]["cv_r2_mean"], 4),
        "cv_r2_std": round(tuning["models"][key]["tuned"]["cv_r2_std"], 4),
    }
    if key == tuning["champion"]:
        ratio = y / pred
        lo, hi = np.percentile(ratio, [10, 90])
        metrics["interval"] = {"coverage": 0.8, "ratio_low": round(float(lo), 3), "ratio_high": round(float(hi), 3),
                               "test_vehicles": int(len(y))}

with open(os.path.join(ROOT, "data", "model_metrics.json"), "w") as f:
    json.dump(metrics, f, indent=2)
print(json.dumps(metrics, indent=2))
