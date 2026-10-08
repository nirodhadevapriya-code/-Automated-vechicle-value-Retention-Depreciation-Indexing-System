"""Compute the facts quoted in the technical report and draw its figures.

Run from the final_system folder:   python report/make_figures.py
Outputs: report/figures/*.png and report/facts.json
"""
import json
import os
import warnings

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.patches import FancyBboxPatch
from sklearn.metrics import r2_score

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, "report", "figures")
os.makedirs(FIG, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"], "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150, "savefig.bbox": "tight",
})
BLUE, GREY, RED = "#1f4e8c", "#8a94a3", "#b42318"

facts = {}
raw = pd.read_csv(os.path.join(ROOT, "data", "raw_car_price_prediction.csv"))
facts["raw_rows"], facts["raw_cols"] = raw.shape
facts["raw_price"] = {k: float(v) for k, v in raw["Price"].describe()[["min", "50%", "mean", "max"]].items()}
facts["raw_price_skew"] = float(raw["Price"].skew())
facts["levy_dash"] = int((raw["Levy"] == "-").sum())
facts["levy_dash_pct"] = round(float((raw["Levy"] == "-").mean() * 100), 1)
facts["n_manufacturers"] = int(raw["Manufacturer"].nunique())
facts["n_models"] = int(raw["Model"].nunique())
facts["year_min"], facts["year_max"] = int(raw["Prod. year"].min()), int(raw["Prod. year"].max())
facts["doors_values"] = raw["Doors"].value_counts().to_dict()
facts["wheel_counts"] = raw["Wheel"].value_counts().to_dict()
facts["dup_with_id"] = int(raw.duplicated().sum())

# ---- cleaning, replicating the Stage 4 notebook step by step
steps = []
df = raw.drop(columns=["ID"])
steps.append(("Raw dataset (ID dropped)", len(df)))
facts["dup_without_id"] = int(df.duplicated().sum())
df = df.drop_duplicates()
steps.append(("After removing duplicate listings", len(df)))
df["Mileage"] = pd.to_numeric(df["Mileage"].astype(str).str.replace(" km", "", regex=False).str.strip(), errors="coerce")
df["Is_Turbo"] = df["Engine volume"].astype(str).str.contains("Turbo", case=False, na=False).astype(int)
df["Engine_displacement"] = pd.to_numeric(df["Engine volume"].astype(str).str.replace(" Turbo", "", regex=False).str.strip(), errors="coerce")
df["Levy"] = pd.to_numeric(df["Levy"].replace("-", np.nan), errors="coerce")
conds = {
    "Price between $500 and $150,000": df["Price"].between(500, 150000),
    "Mileage between 10 and 500,000 km": df["Mileage"].between(10, 500000),
    "Engine volume between 0.5 and 7.0 L": df["Engine_displacement"].between(0.5, 7.0),
    "Production year between 1980 and 2026": df["Prod. year"].between(1980, 2026),
}
facts["failing_each_rule"] = {k: int((~v).sum()) for k, v in conds.items()}
mask = np.logical_and.reduce(list(conds.values()))
df = df[mask].copy()
steps.append(("After domain-range filters", len(df)))
facts["cleaning_steps"] = steps
facts["levy_missing_after_clean"] = int(df["Levy"].isna().sum())
facts["levy_missing_pct_after_clean"] = round(float(df["Levy"].isna().mean() * 100), 1)
facts["clean_price"] = {k: float(v) for k, v in df["Price"].describe()[["min", "25%", "50%", "75%", "max", "mean"]].items()}
facts["clean_price_skew"] = float(df["Price"].skew())
facts["clean_log_skew"] = float(np.log1p(df["Price"]).skew())
df["Age"] = 2026 - df["Prod. year"]
facts["wheel_mean_price"] = df.groupby("Wheel")["Price"].mean().round(0).to_dict()
facts["wheel_median_price"] = df.groupby("Wheel")["Price"].median().round(0).to_dict()
facts["wheel_count_clean"] = df["Wheel"].value_counts().to_dict()
corr = df[["Price", "Levy", "Engine_displacement", "Mileage", "Cylinders", "Airbags", "Age"]].corr()
facts["corr_price"] = corr["Price"].round(2).to_dict()
facts["corr_disp_cyl"] = round(float(corr.loc["Engine_displacement", "Cylinders"]), 2)
facts["corr_age_mileage"] = round(float(corr.loc["Age", "Mileage"]), 2)
facts["luxury_mean_price"] = None
lux = {"MERCEDES-BENZ", "BMW", "LEXUS", "PORSCHE", "AUDI", "LAND ROVER", "JAGUAR", "MASERATI", "BENTLEY", "FERRARI", "ASTON MARTIN", "CADILLAC"}
df["lux"] = df["Manufacturer"].str.upper().isin(lux)
facts["luxury_mean_price"] = df.groupby("lux")["Price"].mean().round(0).to_dict()
facts["fuel_counts"] = df["Fuel type"].value_counts().to_dict()
facts["hybrid_mean_price"] = df.groupby("Fuel type")["Price"].mean().round(0).to_dict()
facts["year_2019_2020_pct_of_clean"] = round(float((df["Prod. year"] >= 2019).mean() * 100), 1)
facts["clean_year_max"] = int(df["Prod. year"].max())

train = pd.read_csv(os.path.join(ROOT, "data", "train_processed.csv"))
test = pd.read_csv(os.path.join(ROOT, "data", "test_processed.csv"))
features = [c for c in train.columns if not c.startswith("Target_")]
facts["n_features"] = len(features)
facts["train_rows"], facts["test_rows"] = len(train), len(test)
fp = lambda d: d[features].round(6).astype(str).agg("|".join, axis=1)
facts["test_rows_in_train"] = int(fp(test).isin(set(fp(train))).sum())

# ---- Figures: EDA
fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
ax[0].hist(raw["Price"].clip(upper=100000), bins=60, color=BLUE)
ax[0].set_title("Raw price (values above $100,000 clipped for display)")
ax[0].set_xlabel("Price (USD)"); ax[0].set_ylabel("Listings")
ax[1].hist(np.log1p(df["Price"]), bins=50, color=BLUE)
ax[1].set_title("ln(1 + price) after cleaning")
ax[1].set_xlabel("ln(1 + price)")
plt.tight_layout(); plt.savefig(os.path.join(FIG, "fig_price_distribution.png")); plt.close()

fig, ax = plt.subplots(figsize=(5.2, 3.4))
order = ["Left wheel", "Right-hand drive"]
sns.boxplot(data=df, x="Wheel", y="Price", order=order, color="#c9d7ea", fliersize=1.5, ax=ax)
ax.set_ylim(0, 80000); ax.set_xlabel(""); ax.set_ylabel("Price (USD)")
ax.set_title("Price by steering wheel position")
plt.tight_layout(); plt.savefig(os.path.join(FIG, "fig_wheel_price.png")); plt.close()

fig, ax = plt.subplots(figsize=(6.2, 3.6))
sub = df[df["Fuel type"].isin(["Petrol", "Diesel", "Hybrid"]) & (df["Age"] <= 30)]
sns.lineplot(data=sub, x="Age", y="Price", hue="Fuel type", errorbar=None,
             palette={"Petrol": BLUE, "Diesel": RED, "Hybrid": "#2f7d4f"}, ax=ax)
ax.set_xlabel("Vehicle age (years, 2026 minus production year)"); ax.set_ylabel("Mean price (USD)")
ax.set_title("Mean price by age and fuel type")
plt.tight_layout(); plt.savefig(os.path.join(FIG, "fig_depreciation.png")); plt.close()

fig, ax = plt.subplots(figsize=(5.4, 4.4))
labels = ["Price", "Levy", "Engine\nvolume", "Mileage", "Cylinders", "Airbags", "Age"]
sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", vmin=-1, vmax=1, xticklabels=labels, yticklabels=labels,
            cbar_kws={"shrink": 0.8}, ax=ax)
ax.set_title("Correlation of numeric variables")
plt.tight_layout(); plt.savefig(os.path.join(FIG, "fig_correlation.png")); plt.close()

fig, ax = plt.subplots(figsize=(6.4, 3.2))
names = [s[0] for s in steps]; counts = [s[1] for s in steps]
ax.barh(range(len(steps))[::-1], counts, color=BLUE)
ax.set_yticks(range(len(steps))[::-1]); ax.set_yticklabels(names)
for i, c in zip(range(len(steps))[::-1], counts):
    ax.text(c + 150, i, f"{c:,}", va="center")
ax.set_xlim(0, max(counts) * 1.15); ax.set_xlabel("Records")
ax.set_title("Records retained at each cleaning step")
plt.tight_layout(); plt.savefig(os.path.join(FIG, "fig_cleaning_steps.png")); plt.close()

# ---- Figures: models
with open(os.path.join(ROOT, "data", "tuning_results.json")) as f:
    tuning = json.load(f)
with open(os.path.join(ROOT, "data", "model_metrics.json")) as f:
    metrics = json.load(f)
label = {"ridge": "Ridge", "random_forest": "Random Forest", "lightgbm": "LightGBM", "xgboost": "XGBoost"}
keys = ["ridge", "random_forest", "lightgbm", "xgboost"]
x = np.arange(len(keys)); w = 0.38
fig, ax = plt.subplots(1, 2, figsize=(9.2, 3.5))
ax[0].bar(x - w / 2, [tuning["models"][k]["baseline"]["cv_r2_mean"] for k in keys], w, label="Baseline", color=GREY)
ax[0].bar(x + w / 2, [tuning["models"][k]["tuned"]["cv_r2_mean"] for k in keys], w,
          yerr=[tuning["models"][k]["tuned"]["cv_r2_std"] for k in keys], capsize=3, label="Tuned", color=BLUE)
ax[0].set_xticks(x); ax[0].set_xticklabels([label[k] for k in keys], fontsize=9)
ax[0].set_ylim(0, 0.9); ax[0].set_ylabel("5-fold CV R² (training split)"); ax[0].legend(frameon=False)
ax[0].set_title("Cross-validated R²")
ax[1].bar(x - w / 2, [tuning["models"][k]["baseline"]["r2"] for k in keys], w, label="Baseline", color=GREY)
ax[1].bar(x + w / 2, [tuning["models"][k]["tuned"]["r2"] for k in keys], w, label="Tuned", color=BLUE)
ax[1].set_xticks(x); ax[1].set_xticklabels([label[k] for k in keys], fontsize=9)
ax[1].set_ylim(0, 0.9); ax[1].set_ylabel("Hold-out test R²"); ax[1].set_title("Test R²")
plt.tight_layout(); plt.savefig(os.path.join(FIG, "fig_model_comparison.png")); plt.close()

champ = joblib.load(os.path.join(ROOT, "models", "xgboost.joblib"))
pred = np.clip(champ.predict(test[features]), 500, 150000)
y = test["Target_Price"].to_numpy()
fig, ax = plt.subplots(1, 2, figsize=(9.2, 3.8))
ax[0].scatter(y, pred, s=5, alpha=0.35, color=BLUE)
m = max(y.max(), pred.max()); ax[0].plot([0, m], [0, m], color=RED, lw=1.2)
ax[0].set_xlabel("Actual price (USD)"); ax[0].set_ylabel("Predicted price (USD)"); ax[0].set_title("Actual vs predicted (test set)")
ax[1].scatter(pred, y - pred, s=5, alpha=0.35, color=BLUE); ax[1].axhline(0, color=RED, lw=1.2)
ax[1].set_xlabel("Predicted price (USD)"); ax[1].set_ylabel("Residual (actual - predicted)"); ax[1].set_title("Residuals vs predicted")
plt.tight_layout(); plt.savefig(os.path.join(FIG, "fig_actual_vs_predicted.png")); plt.close()

imp = pd.Series(champ.feature_importances_, index=features).sort_values(ascending=False).head(12)[::-1]
fig, ax = plt.subplots(figsize=(6.2, 3.9))
ax.barh(imp.index, imp.values, color=BLUE); ax.set_xlabel("Relative importance (gain)")
ax.set_title("Top 12 features in the final XGBoost model")
plt.tight_layout(); plt.savefig(os.path.join(FIG, "fig_feature_importance.png")); plt.close()
facts["top_features"] = {k: round(float(v), 3) for k, v in imp[::-1].items()}

ape = np.abs(y - pred) / y
facts["final_test"] = {"r2": round(float(r2_score(y, pred)), 4), "median_ape": round(float(np.median(ape)), 3),
                       "within_15pct": round(float((ape <= 0.15).mean()), 3), "within_25pct": round(float((ape <= 0.25).mean()), 3)}
bands = pd.cut(y, [0, 3000, 8000, 15000, 30000, 200000], labels=["under 3k", "3k-8k", "8k-15k", "15k-30k", "over 30k"])
band = pd.DataFrame({"band": bands, "ae": np.abs(y - pred), "ape": ape}).groupby("band", observed=True).agg(
    n=("ae", "size"), mae=("ae", "mean"), median_ape=("ape", "median"))
facts["error_by_price_band"] = {k: {"n": int(r.n), "mae": round(float(r.mae)), "median_ape": round(float(r.median_ape), 3)} for k, r in band.iterrows()}

# ---- Architecture diagram
fig, ax = plt.subplots(figsize=(9, 3.6)); ax.axis("off"); ax.set_xlim(0, 100); ax.set_ylim(0, 40)
def box(x0, y0, w, h, text, fc="#eef3fa"):
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle="round,pad=0.3,rounding_size=1", fc=fc, ec="#1f4e8c", lw=1.1))
    ax.text(x0 + w / 2, y0 + h / 2, text, ha="center", va="center", fontsize=9)
def arrow(x0, y0, x1, y1):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="->", color="#1f4e8c", lw=1.2))
box(1, 15, 17, 12, "Web browser\n(index.html,\napp.js)")
box(26, 15, 17, 12, "Flask service\n(app.py)\n/api/predict")
box(51, 25, 20, 11, "VehiclePreprocessor\nvalidation + features\n+ fitted pipeline", "#ffffff")
box(51, 4, 20, 11, "ModelService\nXGBoost, LightGBM,\nRandom Forest, Ridge", "#ffffff")
box(79, 15, 19, 12, "Result\nprice, range,\nasking-price check,\nmodel comparison", "#f4f7fb")
arrow(18, 21, 26, 21); arrow(43, 24, 51, 30); arrow(61, 25, 61, 15); arrow(43, 18, 51, 10)
arrow(71, 10, 79, 18); arrow(26, 19, 18, 19)
ax.text(22, 29, "JSON request / response", ha="center", fontsize=8, style="italic")
plt.tight_layout(); plt.savefig(os.path.join(FIG, "fig_architecture.png")); plt.close()

with open(os.path.join(ROOT, "report", "facts.json"), "w") as f:
    json.dump(facts, f, indent=2, default=str)
print(json.dumps(facts, indent=2, default=str))
