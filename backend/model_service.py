"""
Stage 9 - model loading and prediction.
"""

import json
import os

import joblib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR = os.path.join(BASE_DIR, "data")

MODEL_LABELS = {
    "xgboost": "XGBoost",
    "lightgbm": "LightGBM",
    "random_forest": "Random Forest",
    "ridge": "Ridge Regression",
}

# Prices outside this range were removed during training, so predictions are kept inside it.
PRICE_FLOOR, PRICE_CEILING = 500.0, 150000.0


class ModelService:
    def __init__(self):
        with open(os.path.join(DATA_DIR, "model_metrics.json")) as f:
            self.metrics = json.load(f)
        self.champion = self.metrics["champion"]
        self.models = {key: joblib.load(os.path.join(MODELS_DIR, f"{key}.joblib")) for key in self.metrics["models"]}

    def predict(self, features, key=None):
        key = key or self.champion
        if key not in self.models:
            raise KeyError(key)
        value = float(self.models[key].predict(features)[0])
        return max(PRICE_FLOOR, min(PRICE_CEILING, value))

    def price_range(self, price):
        """Range that contained the actual price for 80% of the hold-out test vehicles."""
        band = self.metrics["interval"]
        return price * band["ratio_low"], price * band["ratio_high"]

    def describe(self):
        return {
            "final_model": self.champion,
            "selection_rule": self.metrics["selection_rule"],
            "models": [
                {"key": key, "name": MODEL_LABELS[key], "final": key == self.champion, **vals}
                for key, vals in sorted(self.metrics["models"].items(), key=lambda kv: -kv[1]["cv_r2"])
            ],
            "interval": self.metrics["interval"],
        }
