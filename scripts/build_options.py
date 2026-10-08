"""Build data/vehicle_options.json (dropdown values) from the raw dataset.

Run from the final_system folder:   python scripts/build_options.py
"""
import json
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
raw = pd.read_csv(os.path.join(ROOT, "data", "raw_car_price_prediction.csv"))

options = {
    "manufacturers": sorted(raw["Manufacturer"].dropna().str.strip().unique(), key=str.upper),
    "colors": sorted(raw["Color"].dropna().str.strip().unique(), key=str.lower),
}
with open(os.path.join(ROOT, "data", "vehicle_options.json"), "w") as f:
    json.dump(options, f, indent=2)
print({k: len(v) for k, v in options.items()})
