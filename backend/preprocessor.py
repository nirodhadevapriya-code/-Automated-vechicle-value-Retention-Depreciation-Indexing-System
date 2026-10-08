"""
Stage 9 - input validation and preprocessing.

Validates the raw user input and rebuilds exactly the features used in training
(Stage 4), then applies the fitted ColumnTransformer saved during training.
"""

import json
import os

import joblib
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Age was computed as (2026 - production year) during training, so the same
# reference year must be used when serving predictions.
REFERENCE_YEAR = 2026

# The training data contains vehicles produced between 1980 and 2020.
MIN_YEAR, MAX_YEAR = 1980, 2020

LUXURY_MAKES = {
    "MERCEDES-BENZ", "BMW", "LEXUS", "PORSCHE", "AUDI", "LAND ROVER",
    "JAGUAR", "MASERATI", "BENTLEY", "FERRARI", "ASTON MARTIN", "CADILLAC",
}

NUMERIC_COLUMNS = ["Age", "Mileage", "Mileage_per_year", "Engine_displacement", "Cylinders", "Airbags", "Levy"]
CATEGORICAL_COLUMNS = [
    "Manufacturer_grouped", "Category", "Leather interior", "Fuel type",
    "Gear box type", "Drive wheels", "Doors", "Wheel", "Color_grouped",
]
BINARY_COLUMNS = ["Is_Turbo", "Is_Luxury_Make"]


class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("Invalid input")
        self.errors = errors


def _number(raw, field, label, lo, hi, errors, integer=False, required=True):
    """Parse a number and check its range. Returns None (and records an error) if invalid."""
    if raw is None or str(raw).strip() == "":
        if required:
            errors[field] = f"{label} is required."
        return None
    text = str(raw).replace(",", "").strip().lower().replace("km", "").strip()
    try:
        value = float(text)
    except ValueError:
        errors[field] = f"{label} must be a number."
        return None
    if value != value or value in (float("inf"), float("-inf")):
        errors[field] = f"{label} must be a finite number."
        return None
    if integer and value != int(value):
        errors[field] = f"{label} must be a whole number."
        return None
    if value < lo or value > hi:
        errors[field] = f"{label} must be between {lo:g} and {hi:g}."
        return None
    return int(value) if integer else value


def _choice(raw, field, label, options, errors):
    value = "" if raw is None else str(raw).strip()
    if value == "":
        errors[field] = f"{label} is required."
        return None
    lookup = {o.lower(): o for o in options}
    if value.lower() not in lookup:
        errors[field] = f"{label} must be one of the listed options."
        return None
    return lookup[value.lower()]


class VehiclePreprocessor:
    def __init__(self):
        self.pipeline = joblib.load(os.path.join(DATA_DIR, "preprocessing_pipeline.joblib"))
        encoder = self.pipeline.named_transformers_["cat"]
        cats = dict(zip(CATEGORICAL_COLUMNS, encoder.categories_))
        self.top_makes = set(cats["Manufacturer_grouped"])
        self.top_colors = set(cats["Color_grouped"])
        self.options = {
            "category": sorted(cats["Category"]),
            "fuel_type": sorted(cats["Fuel type"]),
            "gearbox": sorted(cats["Gear box type"]),
            "drive_wheels": sorted(cats["Drive wheels"]),
            "doors": list(cats["Doors"]),
            "wheel": list(cats["Wheel"]),
            "leather": ["Yes", "No"],
        }
        with open(os.path.join(DATA_DIR, "vehicle_options.json")) as f:
            extra = json.load(f)
        self.options["manufacturer"] = extra["manufacturers"]
        self.options["color"] = extra["colors"]
        with open(os.path.join(DATA_DIR, "levy_imputation_medians.json")) as f:
            levy = json.load(f)
        self.global_levy = float(levy["global_median"])
        self.make_levy = levy.get("mfg_medians", {})
        self.feature_names = NUMERIC_COLUMNS + list(encoder.get_feature_names_out(CATEGORICAL_COLUMNS)) + BINARY_COLUMNS

    # ------------------------------------------------------------------ validation
    def validate(self, data):
        """Return (clean_values, notices). Raises ValidationError with per-field messages."""
        if not isinstance(data, dict):
            raise ValidationError({"_form": "Request body must be a JSON object."})
        errors, notices = {}, []
        g = data.get

        year = _number(g("prod_year"), "prod_year", "Production year", MIN_YEAR, MAX_YEAR, errors, integer=True)
        mileage = _number(g("mileage"), "mileage", "Mileage (km)", 0, 1_000_000, errors)
        engine = _number(g("engine_volume"), "engine_volume", "Engine volume (L)", 0.5, 7.0, errors)
        cylinders = _number(g("cylinders"), "cylinders", "Cylinders", 1, 16, errors, integer=True)
        airbags = _number(g("airbags"), "airbags", "Airbags", 0, 16, errors, integer=True)
        levy = _number(g("levy"), "levy", "Customs levy (USD)", 0, 20_000, errors, required=False)
        asking = _number(g("asking_price"), "asking_price", "Asking price (USD)", 1, 1_000_000, errors, required=False)

        category = _choice(g("category"), "category", "Body category", self.options["category"], errors)
        fuel = _choice(g("fuel_type"), "fuel_type", "Fuel type", self.options["fuel_type"], errors)
        gearbox = _choice(g("gearbox"), "gearbox", "Gear box", self.options["gearbox"], errors)
        drive = _choice(g("drive_wheels"), "drive_wheels", "Drive wheels", self.options["drive_wheels"], errors)
        doors = _choice(g("doors"), "doors", "Doors", self.options["doors"], errors)
        wheel = _choice(g("wheel"), "wheel", "Steering wheel", self.options["wheel"], errors)
        leather = _choice(g("leather"), "leather", "Leather interior", self.options["leather"], errors)
        make = _choice(g("manufacturer"), "manufacturer", "Manufacturer", self.options["manufacturer"], errors)
        color = _choice(g("color"), "color", "Colour", self.options["color"], errors)

        turbo_raw = g("turbo", False)
        if isinstance(turbo_raw, str):
            turbo_raw = turbo_raw.strip().lower() in ("1", "true", "yes", "on")
        turbo = 1 if turbo_raw else 0

        if errors:
            raise ValidationError(errors)

        levy_imputed = levy is None
        if levy_imputed:
            levy = float(self.make_levy.get(make.upper(), self.global_levy))
            notices.append(f"Customs levy was not provided; the training-set median for this make (${levy:,.0f}) was used.")

        age = REFERENCE_YEAR - year
        clean = {
            "Age": age,
            "Mileage": mileage,
            "Mileage_per_year": mileage / (age + 1.0),
            "Engine_displacement": engine,
            "Cylinders": cylinders,
            "Airbags": airbags,
            "Levy": levy,
            "Manufacturer_grouped": make.upper() if make.upper() in self.top_makes else "Other",
            "Category": category,
            "Leather interior": leather,
            "Fuel type": fuel,
            "Gear box type": gearbox,
            "Drive wheels": drive,
            "Doors": doors,
            "Wheel": wheel,
            "Color_grouped": color if color in self.top_colors else "Other",
            "Is_Turbo": turbo,
            "Is_Luxury_Make": 1 if make.upper() in LUXURY_MAKES else 0,
        }
        summary = {
            "manufacturer": make, "prod_year": year, "mileage": mileage, "levy": levy,
            "levy_imputed": levy_imputed, "asking_price": asking,
        }
        return clean, summary, notices

    # ---------------------------------------------------------------- transformation
    def transform(self, clean):
        row = pd.DataFrame([{c: clean[c] for c in NUMERIC_COLUMNS + CATEGORICAL_COLUMNS + BINARY_COLUMNS}])
        return pd.DataFrame(self.pipeline.transform(row), columns=self.feature_names)

    def get_options(self):
        return {**self.options, "year_range": [MIN_YEAR, MAX_YEAR]}
