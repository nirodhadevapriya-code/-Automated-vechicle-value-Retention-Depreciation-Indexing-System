"""Stage 9/10 tests: validation, prediction and page rendering.

Run from the final_system folder:   python -m unittest discover -s tests -v
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402

VALID = {
    "manufacturer": "TOYOTA", "prod_year": 2012, "category": "Sedan", "color": "Silver",
    "engine_volume": 2.0, "cylinders": 4, "turbo": False, "fuel_type": "Petrol", "gearbox": "Automatic",
    "drive_wheels": "Front", "wheel": "Left wheel", "mileage": 120000, "airbags": 8, "doors": "4-5",
    "leather": "No",
}


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def post(self, **overrides):
        body = {**VALID, **overrides}
        body = {k: v for k, v in body.items() if v is not None}
        res = self.client.post("/api/predict", data=json.dumps(body), content_type="application/json")
        return res.status_code, res.get_json()

    def test_valid_prediction(self):
        status, data = self.post()
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        p = data["prediction"]
        self.assertGreaterEqual(p["price_usd"], 500)
        self.assertLess(p["range_low"], p["price_usd"])
        self.assertGreater(p["range_high"], p["price_usd"])
        self.assertEqual(len(data["model_comparison"]), 4)
        self.assertTrue(any("levy" in n.lower() for n in data["notices"]))

    def test_every_model_can_be_selected(self):
        for key in ("xgboost", "lightgbm", "random_forest", "ridge"):
            status, data = self.post(model=key)
            self.assertEqual(status, 200)
            self.assertEqual(data["prediction"]["model"], key)

    def test_unknown_model_rejected(self):
        status, data = self.post(model="foo")
        self.assertEqual(status, 400)
        self.assertIn("model", data["errors"])

    def test_missing_required_fields(self):
        status, data = self.post(prod_year=None, mileage=None, manufacturer=None)
        self.assertEqual(status, 400)
        for field in ("prod_year", "mileage", "manufacturer"):
            self.assertIn(field, data["errors"])

    def test_invalid_values_rejected(self):
        cases = {
            "prod_year": ["abc", 2026, 1850, "2012.5"],
            "mileage": ["xyz", -5, "inf", "nan", 5_000_000],
            "engine_volume": ["9.9", "abc", 0],
            "cylinders": [0, 3.5, "x"],
            "airbags": [-1, 99],
            "levy": [-10, "abc"],
            "asking_price": [-5, "nan", 0],
            "fuel_type": ["Electric"],
            "color": ["Plaid"],
        }
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    status, data = self.post(**{field: value})
                    self.assertEqual(status, 400)
                    self.assertIn(field, data["errors"])

    def test_year_range_is_training_range(self):
        self.assertEqual(self.post(prod_year=1980)[0], 200)
        self.assertEqual(self.post(prod_year=2020)[0], 200)
        self.assertEqual(self.post(prod_year=2021)[0], 400)

    def test_turbo_flag_does_not_change_other_fields(self):
        _, a = self.post(turbo="false")
        _, b = self.post(turbo=False)
        self.assertEqual(a["prediction"]["price_usd"], b["prediction"]["price_usd"])
        _, c = self.post(turbo=True)
        self.assertTrue(c["success"])

    def test_asking_price_check(self):
        _, base = self.post()
        price = base["prediction"]["price_usd"]
        _, high = self.post(asking_price=price * 3)
        _, low = self.post(asking_price=price / 3)
        self.assertEqual(high["asking_price_check"]["position"], "above")
        self.assertEqual(low["asking_price_check"]["position"], "below")
        self.assertIsNone(base["asking_price_check"])

    def test_bad_request_bodies(self):
        res = self.client.post("/api/predict", data=b"{bad", content_type="application/json")
        self.assertEqual(res.status_code, 400)
        res = self.client.post("/api/predict", data=json.dumps([1, 2]), content_type="application/json")
        self.assertEqual(res.status_code, 400)
        res = self.client.get("/api/predict")
        self.assertEqual(res.status_code, 405)

    def test_options_and_models(self):
        options = self.client.get("/api/options").get_json()
        self.assertEqual(options["year_range"], [1980, 2020])
        self.assertIn("TOYOTA", options["manufacturer"])
        models = self.client.get("/api/models").get_json()
        self.assertEqual(len(models["models"]), 4)
        self.assertEqual(sum(m["final"] for m in models["models"]), 1)

    def test_page_renders(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Estimate price", res.data)
        for section in (b'id="analysis"', b'id="cars"', b'id="models"', b'id="presentation"', b'id="contact"', b"<footer"):
            self.assertIn(section, res.data)

    def test_insights(self):
        data = self.client.get("/api/insights").get_json()
        for key in ("kpis", "importance", "age_price", "body", "models", "scatter", "funnel", "facts"):
            self.assertIn(key, data)
        self.assertEqual(len(data["models"]), 4)
        self.assertEqual(sum(m["final"] for m in data["models"]), 1)
        self.assertAlmostEqual(sum(i["value"] for i in data["importance"]), 100, delta=1)

    def test_static_assets(self):
        for path in ("/static/css/style.css", "/static/js/site.js", "/static/js/app.js", "/static/js/cars.js",
                     "/static/vendor/chart.umd.min.js", "/static/fonts/inter-var-latin.woff2"):
            self.assertEqual(self.client.get(path).status_code, 200, path)


if __name__ == "__main__":
    unittest.main()
