"""Compute the numbers shown in the website's charts, callouts and presentation (data/insights.json).

Run from the final_system folder after stage7_tuning.py and build_metrics.py:
    python scripts/build_insights.py
"""
import json
import os
import warnings

import joblib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda f: os.path.join(ROOT, "data", f)

raw = pd.read_csv(D("raw_car_price_prediction.csv"))
n_raw = len(raw)
df = raw.drop(columns=["ID"])
n_dedup = len(df.drop_duplicates())
df = df.drop_duplicates()
df["Mileage"] = pd.to_numeric(df["Mileage"].astype(str).str.replace(" km", "", regex=False).str.strip(), errors="coerce")
df["Engine_displacement"] = pd.to_numeric(df["Engine volume"].astype(str).str.replace(" Turbo", "", regex=False).str.strip(), errors="coerce")
df["Levy"] = pd.to_numeric(df["Levy"].replace("-", np.nan), errors="coerce")
keep = (df["Price"].between(500, 150000) & df["Mileage"].between(10, 500000)
        & df["Engine_displacement"].between(0.5, 7.0) & df["Prod. year"].between(1980, 2026))
df = df[keep].copy()
df["Age"] = 2026 - df["Prod. year"]
n_clean = len(df)

metrics = json.load(open(D("model_metrics.json")))
tuning = json.load(open(D("tuning_results.json")))
ablation = json.load(open(D("ablation_results.json")))
facts = json.load(open(os.path.join(ROOT, "report", "facts.json")))

out = {}
out["kpis"] = {
    "raw_records": n_raw, "clean_records": n_clean, "features": 57, "models": 4,
    "train": 11208, "test": 2803,
    "final_r2": metrics["models"][metrics["champion"]]["test_r2"],
    "final_mae": metrics["models"][metrics["champion"]]["test_mae"],
    "median_ape": facts["final_test"]["median_ape"],
    "within_15": facts["final_test"]["within_15pct"],
    "within_25": facts["final_test"]["within_25pct"],
    "interval": metrics["interval"],
    "median_price": float(df["Price"].median()),
}
out["facts"] = {"q1": facts["clean_price"]["25%"], "q3": facts["clean_price"]["75%"],
                 "recent_pct": facts["year_2019_2020_pct_of_clean"] / 100}
out["funnel"] = [
    {"label": "Listings downloaded", "n": n_raw},
    {"label": "After removing repeated listings", "n": n_dedup},
    {"label": "After removing unrealistic values", "n": n_clean},
]

# ---- importance grouped by meaning
model = joblib.load(os.path.join(ROOT, "models", "xgboost.joblib"))
test = pd.read_csv(D("test_processed.csv"))
features = [c for c in test.columns if not c.startswith("Target_")]
def group(name):
    for prefix, label in [("Manufacturer_grouped_", "Make"), ("Category_", "Body type"), ("Fuel type_", "Fuel type"),
                          ("Gear box type_", "Gear box"), ("Drive wheels_", "Drive wheels"), ("Doors_", "Doors"),
                          ("Wheel_", "Steering side"), ("Color_grouped_", "Colour"), ("Leather interior_", "Leather")]:
        if name.startswith(prefix):
            return label
    return {"Age": "Age", "Mileage": "Mileage", "Mileage_per_year": "Mileage", "Engine_displacement": "Engine size",
            "Cylinders": "Cylinders", "Airbags": "Airbags", "Levy": "Customs levy", "Is_Turbo": "Turbo",
            "Is_Luxury_Make": "Luxury make"}[name]

# Permutation importance of each group of columns: how much R2 is lost on the hold-out cars when that
# information is shuffled between cars. (Gain-based importance spreads over correlated columns and understates Age.)
from sklearn.metrics import r2_score
groups = {}
for c in features:
    groups.setdefault(group(c), []).append(c)
y_test = test["Target_Price"].to_numpy()
base_r2 = r2_score(y_test, np.clip(model.predict(test[features]), 500, 150000))
rng0 = np.random.default_rng(0)
drops = {}
for g, cols in groups.items():
    losses = []
    for _ in range(5):
        shuffled = test[features].copy()
        perm = rng0.permutation(len(shuffled))
        shuffled[cols] = shuffled[cols].to_numpy()[perm]
        losses.append(base_r2 - r2_score(y_test, np.clip(model.predict(shuffled), 500, 150000)))
    drops[g] = max(float(np.mean(losses)), 0.0)
grouped = pd.Series(drops).sort_values(ascending=False)
out["importance_r2_drop"] = {k: round(v, 3) for k, v in grouped.items()}
grouped = grouped / grouped.sum() * 100
out["importance"] = [{"name": k, "value": round(float(v), 1)} for k, v in grouped.items()]

# ---- price against age
ages = list(range(6, 36))
series = {}
for label, sub in [("All cars", df), ("Petrol", df[df["Fuel type"] == "Petrol"]), ("Diesel", df[df["Fuel type"] == "Diesel"]),
                   ("Hybrid", df[df["Fuel type"] == "Hybrid"])]:
    g = sub.groupby("Age")["Price"].agg(["median", "size"])
    series[label] = [round(float(g.loc[a, "median"])) if a in g.index and g.loc[a, "size"] >= 15 else None for a in ages]
out["age_price"] = {"ages": ages, "series": series}

# ---- body types, fuel, makes, wheel
def summary(col, top=None):
    g = df.groupby(col).agg(n=("Price", "size"), median=("Price", "median"), age=("Age", "median"), km=("Mileage", "median"))
    g = g.sort_values("n", ascending=False)
    if top:
        g = g.head(top)
    return [{"name": k, "n": int(r.n), "median": round(float(r["median"])), "age": round(float(r.age)), "km": round(float(r.km), -3)} for k, r in g.iterrows()]
out["body"] = summary("Category")
out["fuel"] = summary("Fuel type", 5)
out["makes"] = summary("Manufacturer", 10)
out["wheel"] = {k: {"n": int(r.n), "median": round(float(r["median"]))} for k, r in df.groupby("Wheel").agg(n=("Price", "size"), median=("Price", "median")).iterrows()}
out["gearbox"] = summary("Gear box type")
out["drive"] = summary("Drive wheels")

# ---- price histogram
edges = list(range(0, 60001, 4000))
counts, _ = np.histogram(df["Price"].clip(upper=59999), bins=edges)
out["price_hist"] = {"edges": edges, "counts": [int(c) for c in counts], "over_60k": int((df["Price"] >= 60000).sum())}

# ---- correlation with price
num = df[["Price", "Age", "Mileage", "Engine_displacement", "Cylinders", "Airbags", "Levy"]].corr()["Price"].drop("Price")
names = {"Age": "Age", "Mileage": "Mileage", "Engine_displacement": "Engine size", "Cylinders": "Cylinders", "Airbags": "Airbags", "Levy": "Customs levy"}
out["corr"] = [{"name": names[k], "value": round(float(v), 2)} for k, v in num.sort_values().items()]

# ---- models
rows = []
for key in ["xgboost", "lightgbm", "random_forest", "ridge"]:
    t = tuning["models"][key]
    rows.append({"key": key, "cv_base": round(t["baseline"]["cv_r2_mean"], 4), "cv_tuned": round(t["tuned"]["cv_r2_mean"], 4),
                 "cv_sd": round(t["tuned"]["cv_r2_std"], 4), "test_base": round(t["baseline"]["r2"], 4),
                 "test_r2": metrics["models"][key]["test_r2"], "rmse": metrics["models"][key]["test_rmse"],
                 "mae": metrics["models"][key]["test_mae"], "final": key == metrics["champion"]})
out["models"] = rows
out["error_band"] = [{"band": k, **v} for k, v in facts["error_by_price_band"].items()]
out["ablation"] = [{"name": k, "cv_r2": v["cv_r2"], "test_r2": v["test_r2"]} for k, v in ablation.items()]

# ---- predicted against actual (sample of the hold-out cars)
pred = np.clip(model.predict(test[features]), 500, 150000)
actual = test["Target_Price"].to_numpy()
rng = np.random.default_rng(7)
idx = rng.choice(len(actual), 450, replace=False)
out["scatter"] = [[int(actual[i]), int(pred[i])] for i in idx if actual[i] < 90000]

with open(D("insights.json"), "w") as f:
    json.dump(out, f, indent=1)
print(json.dumps({k: (v if k in ("kpis", "importance", "funnel", "wheel", "corr") else "...") for k, v in out.items()}, indent=1))
print([b["name"] for b in out["body"]])
