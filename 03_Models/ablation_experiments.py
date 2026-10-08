"""
Stage 7: do feature engineering, feature selection or the target choice improve the final model?

Run from the project root:   python 03_Models/ablation_experiments.py
Uses the tuned XGBoost settings, 5-fold CV on the training split and the hold-out test split.
Output: 03_Models/ablation_results.json
"""
import json
import os
import warnings

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold
from xgboost import XGBRegressor

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "03_Models", "tuning_results.json")) as f:
    params = json.load(f)["models"]["xgboost"]["tuned"]["best_params"]

train = pd.read_csv(os.path.join(ROOT, "02_Data", "train_processed.csv"))
test = pd.read_csv(os.path.join(ROOT, "02_Data", "test_processed.csv"))
all_features = [c for c in train.columns if not c.startswith("Target_")]
y_train, y_test = train["Target_Price"], test["Target_Price"]
cv = KFold(5, shuffle=True, random_state=42)


def evaluate(features, log_target=False):
    scores = []
    for tr, va in cv.split(train):
        m = XGBRegressor(**params, random_state=42, n_jobs=-1)
        y = np.log1p(y_train.iloc[tr]) if log_target else y_train.iloc[tr]
        m.fit(train.iloc[tr][features], y)
        p = m.predict(train.iloc[va][features])
        p = np.expm1(p) if log_target else p
        scores.append(r2_score(y_train.iloc[va], p))
    m = XGBRegressor(**params, random_state=42, n_jobs=-1)
    m.fit(train[features], np.log1p(y_train) if log_target else y_train)
    p = m.predict(test[features])
    p = np.expm1(p) if log_target else p
    return {"n_features": len(features), "cv_r2": round(float(np.mean(scores)), 4),
            "test_r2": round(float(r2_score(y_test, p)), 4), "test_mae": round(float(mean_absolute_error(y_test, p)), 0)}


def without(prefixes):
    return [c for c in all_features if not any(c == p or c.startswith(p + "_") for p in prefixes)]


experiments = {
    "All 57 features (final configuration)": (all_features, False),
    "Without Levy": (without(["Levy"]), False),
    "Without Mileage_per_year": (without(["Mileage_per_year"]), False),
    "Without Is_Turbo and Is_Luxury_Make": (without(["Is_Turbo", "Is_Luxury_Make"]), False),
    "Without colour dummies": (without(["Color_grouped"]), False),
    "Without Age and Mileage_per_year": (without(["Age", "Mileage_per_year"]), False),
    "Log-price target (all features)": (all_features, True),
}
results = {}
for name, (feats, log_t) in experiments.items():
    results[name] = evaluate(feats, log_t)
    print(f"{name:42s} {results[name]}", flush=True)

with open(os.path.join(ROOT, "03_Models", "ablation_results.json"), "w") as f:
    json.dump(results, f, indent=2)
