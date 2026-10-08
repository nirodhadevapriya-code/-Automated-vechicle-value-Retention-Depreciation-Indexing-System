"""
Stage 9 check: does the live backend (validation + preprocessing + model) give the same prediction
as the training pipeline for the same car?

The raw hold-out cars are rebuilt with the Stage 4 cleaning rules and the same split (seed 42), sent through
VehiclePreprocessor.validate/transform and the final model, and compared with the prediction made from
data/test_processed.csv.

Run from the final_system folder:   python scripts/check_serving_consistency.py
Output: data/serving_consistency.json
"""
import json
import os
import sys
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from backend import ModelService, VehiclePreprocessor  # noqa: E402

raw = pd.read_csv(os.path.join(ROOT, "data", "raw_car_price_prediction.csv")).drop(columns=["ID"]).drop_duplicates()
raw["Mileage"] = pd.to_numeric(raw["Mileage"].astype(str).str.replace(" km", "", regex=False).str.strip(), errors="coerce")
raw["Is_Turbo"] = raw["Engine volume"].astype(str).str.contains("Turbo", case=False, na=False).astype(int)
raw["Engine_displacement"] = pd.to_numeric(raw["Engine volume"].astype(str).str.replace(" Turbo", "", regex=False).str.strip(), errors="coerce")
raw["Doors"] = raw["Doors"].map({"04-May": "4-5", "02-Mar": "2-3", ">5": ">5"}).fillna("4-5")
raw["Levy"] = pd.to_numeric(raw["Levy"].replace("-", np.nan), errors="coerce")
keep = (raw["Price"].between(500, 150000) & raw["Mileage"].between(10, 500000)
        & raw["Engine_displacement"].between(0.5, 7.0) & raw["Prod. year"].between(1980, 2026))
raw = raw[keep].reset_index(drop=True)
_, test_raw = train_test_split(raw, test_size=0.20, random_state=42, shuffle=True)
test_raw = test_raw.reset_index(drop=True)

test_proc = pd.read_csv(os.path.join(ROOT, "data", "test_processed.csv"))
features = [c for c in test_proc.columns if not c.startswith("Target_")]
assert len(test_raw) == len(test_proc) and np.allclose(test_raw["Price"], test_proc["Target_Price"]), "split not reproduced"

pre, svc = VehiclePreprocessor(), ModelService()
model = joblib.load(os.path.join(ROOT, "models", "xgboost.joblib"))
reference = model.predict(test_proc[features])

# The levy imputation in training used the exact manufacturer name; the form sends levy empty when unknown.
diffs, rejected = [], 0
served = np.full(len(test_raw), np.nan)
for i, r in test_raw.iterrows():
    body = {
        "manufacturer": r["Manufacturer"], "prod_year": int(r["Prod. year"]), "category": r["Category"], "color": r["Color"],
        "engine_volume": r["Engine_displacement"], "cylinders": int(r["Cylinders"]), "turbo": bool(r["Is_Turbo"]),
        "fuel_type": r["Fuel type"], "gearbox": r["Gear box type"], "drive_wheels": r["Drive wheels"], "wheel": r["Wheel"],
        "mileage": r["Mileage"], "airbags": int(r["Airbags"]), "doors": r["Doors"], "leather": r["Leather interior"],
        "levy": None if pd.isna(r["Levy"]) else r["Levy"],
    }
    try:
        clean, _, _ = pre.validate(body)
    except Exception:
        rejected += 1
        continue
    served[i] = float(model.predict(pre.transform(clean))[0])

ok = ~np.isnan(served)
d = np.abs(served[ok] - reference[ok])
result = {
    "test_cars": int(len(test_raw)),
    "rejected_by_validation": int(rejected),
    "compared": int(ok.sum()),
    "identical_within_$0.01": int((d < 0.01).sum()),
    "max_abs_difference_usd": round(float(d.max()), 4),
    "mean_abs_difference_usd": round(float(d.mean()), 6),
}
print(json.dumps(result, indent=2))
with open(os.path.join(ROOT, "data", "serving_consistency.json"), "w") as f:
    json.dump(result, f, indent=2)
