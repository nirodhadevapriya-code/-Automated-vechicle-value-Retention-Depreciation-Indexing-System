"""
Stage 6-7: baseline comparison, hyperparameter search and final model selection.

Run from the project root:   python 03_Models/stage7_tuning.py

Validation strategy : 5-fold CV (shuffled, seed 42) on the training split only.
Search strategy     : RandomizedSearchCV for Random Forest, LightGBM and XGBoost,
                      RidgeCV (log-spaced alpha grid) for Ridge.
Selection rule      : the tuned model with the highest cross-validated R2 on the
                      training split. The hold-out test split is used once, for
                      reporting only, and is never used to choose a model.
"""

import json
import os
import time
import warnings

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge, RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, RandomizedSearchCV, cross_val_score
from xgboost import XGBRegressor

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "02_Data")
MODELS_DIR = os.path.join(ROOT, "03_Models")
SEED = 42

train = pd.read_csv(os.path.join(DATA_DIR, "train_processed.csv"))
test = pd.read_csv(os.path.join(DATA_DIR, "test_processed.csv"))
features = [c for c in train.columns if not c.startswith("Target_")]
X_train, y_train = train[features], train["Target_Price"]
X_test, y_test = test[features], test["Target_Price"]

cv = KFold(n_splits=5, shuffle=True, random_state=SEED)


def test_metrics(model):
    pred = model.predict(X_test)
    return {
        "r2": float(r2_score(y_test, pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_test, pred))),
        "mae": float(mean_absolute_error(y_test, pred)),
    }


baselines = {
    "ridge": Ridge(alpha=10.0),
    "random_forest": RandomForestRegressor(n_estimators=100, max_depth=15, min_samples_leaf=2,
                                           random_state=SEED, n_jobs=-1),
    "lightgbm": LGBMRegressor(n_estimators=150, learning_rate=0.08, num_leaves=31,
                              random_state=SEED, verbose=-1),
    "xgboost": XGBRegressor(n_estimators=150, max_depth=6, learning_rate=0.08,
                            random_state=SEED, n_jobs=-1),
}

searches = {
    "random_forest": (
        RandomForestRegressor(random_state=SEED, n_jobs=-1),
        {"n_estimators": [150, 250], "max_depth": [12, 16, 20], "min_samples_leaf": [2, 3, 5],
         "min_samples_split": [4, 8], "max_features": [0.5, 0.7, 0.9]},
        10,
    ),
    "lightgbm": (
        LGBMRegressor(random_state=SEED, verbose=-1),
        {"n_estimators": [200, 400, 600], "learning_rate": [0.02, 0.04, 0.08],
         "num_leaves": [15, 31, 63], "min_child_samples": [10, 20, 40],
         "subsample": [0.7, 0.85, 1.0], "subsample_freq": [1],
         "colsample_bytree": [0.6, 0.8, 1.0], "reg_lambda": [0, 1, 5]},
        30,
    ),
    "xgboost": (
        XGBRegressor(random_state=SEED, n_jobs=-1),
        {"n_estimators": [300, 500, 800], "max_depth": [4, 6, 8, 10],
         "learning_rate": [0.02, 0.04, 0.08], "subsample": [0.7, 0.85, 1.0],
         "colsample_bytree": [0.6, 0.8, 1.0], "min_child_weight": [1, 3, 5],
         "reg_lambda": [1, 3, 10]},
        25,
    ),
}

results = {}
fitted = {}

for key, model in baselines.items():
    t0 = time.time()
    scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="r2", n_jobs=1)
    model.fit(X_train, y_train)
    results[key] = {
        "baseline": {"cv_r2_mean": float(scores.mean()), "cv_r2_std": float(scores.std()),
                     **test_metrics(model)},
    }
    print(f"[baseline] {key:14s} CV R2 {scores.mean():.4f} +/- {scores.std():.4f}  "
          f"test R2 {results[key]['baseline']['r2']:.4f}  ({time.time() - t0:.0f}s)", flush=True)

# Ridge: RidgeCV over a logarithmic alpha grid
alphas = np.logspace(-2, 4, 30)
ridge = RidgeCV(alphas=alphas, cv=cv, scoring="r2").fit(X_train, y_train)
ridge_scores = cross_val_score(Ridge(alpha=ridge.alpha_), X_train, y_train, cv=cv, scoring="r2")
results["ridge"]["tuned"] = {"cv_r2_mean": float(ridge_scores.mean()), "cv_r2_std": float(ridge_scores.std()),
                             "best_params": {"alpha": float(ridge.alpha_)}, "search": "RidgeCV, 30 log-spaced alphas",
                             **test_metrics(ridge)}
fitted["ridge"] = ridge
print(f"[tuned]    ridge          CV R2 {ridge_scores.mean():.4f}  alpha={ridge.alpha_:.3f}", flush=True)

for key, (estimator, space, n_iter) in searches.items():
    t0 = time.time()
    search = RandomizedSearchCV(estimator, space, n_iter=n_iter, cv=cv, scoring="r2",
                                random_state=SEED, n_jobs=1, refit=True)
    search.fit(X_train, y_train)
    idx = search.best_index_
    results[key]["tuned"] = {
        "cv_r2_mean": float(search.cv_results_["mean_test_score"][idx]),
        "cv_r2_std": float(search.cv_results_["std_test_score"][idx]),
        "best_params": {k: (v.item() if hasattr(v, "item") else v) for k, v in search.best_params_.items()},
        "search": f"RandomizedSearchCV, {n_iter} candidates x 5 folds",
        **test_metrics(search.best_estimator_),
    }
    fitted[key] = search.best_estimator_
    print(f"[tuned]    {key:14s} CV R2 {results[key]['tuned']['cv_r2_mean']:.4f}  "
          f"test R2 {results[key]['tuned']['r2']:.4f}  ({time.time() - t0:.0f}s)", flush=True)

champion = max(results, key=lambda k: results[k]["tuned"]["cv_r2_mean"])
print(f"\nChampion by cross-validated R2: {champion}", flush=True)

os.makedirs(MODELS_DIR, exist_ok=True)
for key, model in fitted.items():
    joblib.dump(model, os.path.join(MODELS_DIR, f"{key}.joblib"), compress=3)

with open(os.path.join(MODELS_DIR, "tuning_results.json"), "w") as f:
    json.dump({"champion": champion, "selection_rule": "highest 5-fold CV R2 on the training split",
               "models": results}, f, indent=2)
print("Saved the models and tuning_results.json in 03_Models", flush=True)
