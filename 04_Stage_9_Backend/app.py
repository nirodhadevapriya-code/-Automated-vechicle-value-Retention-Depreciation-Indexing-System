"""
IT3051 Fundamentals of Data Mining - Mini Project 2026
Stage 9: prediction service (Flask).  It also serves the Stage 10 website, which lives in its own
folder (05_Stage_10_Website: templates and static files) and talks to this service through /api/*.

Run from this folder:  python app.py      then open http://127.0.0.1:5000
(or from the project root:  python 04_Stage_9_Backend/app.py)
"""

import logging
import os

from flask import Flask, jsonify, render_template, request

from backend import MODEL_LABELS, ModelService, ValidationError, VehiclePreprocessor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WEBSITE_DIR = os.path.join(ROOT, "05_Stage_10_Website")          # Stage 10 (front end)

app = Flask(__name__,
            template_folder=os.path.join(WEBSITE_DIR, "templates"),
            static_folder=os.path.join(WEBSITE_DIR, "static"))
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024
log = logging.getLogger("autovaluate")

preprocessor = VehiclePreprocessor()
models = ModelService()


INSIGHTS_PATH = os.path.join(WEBSITE_DIR, "data", "insights.json")


@app.route("/")
def index():
    # CONTACT_EMAIL (environment variable) is where the contact form opens a draft email to.
    has_video = os.path.exists(os.path.join(app.static_folder, "media", "hero.mp4"))
    return render_template("index.html", contact_email=os.environ.get("CONTACT_EMAIL", ""), has_video=has_video)


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "final_model": models.champion})


@app.route("/api/options")
def options():
    """Dropdown values and allowed ranges for the form."""
    return jsonify(preprocessor.get_options())


@app.route("/api/models")
def model_summary():
    """Evaluation results of the compared models (hold-out test set)."""
    return jsonify(models.describe())


@app.route("/api/insights")
def insights():
    """Numbers behind the charts, callouts and presentation (built by 05_Stage_10_Website/build_insights.py)."""
    with open(INSIGHTS_PATH, encoding="utf-8") as f:
        return app.response_class(f.read(), mimetype="application/json")


@app.route("/api/predict", methods=["POST"])
def predict():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"success": False, "errors": {"_form": "Send the vehicle details as a JSON object."}}), 400

    try:
        clean, summary, notices = preprocessor.validate(payload)
    except ValidationError as exc:
        return jsonify({"success": False, "errors": exc.errors}), 400

    selected = str(payload.get("model") or models.champion).lower()
    if selected not in MODEL_LABELS or selected not in models.models:
        return jsonify({"success": False, "errors": {"model": "Unknown model."}}), 400

    try:
        features = preprocessor.transform(clean)
        price = models.predict(features, selected)
        comparison = [
            {"key": key, "name": MODEL_LABELS[key], "final": key == models.champion,
             "price": round(models.predict(features, key), 2)}
            for key in sorted(models.models, key=lambda k: -models.metrics["models"][k]["cv_r2"])
        ]
    except Exception:
        log.exception("Prediction failed")
        return jsonify({"success": False, "errors": {"_form": "The prediction could not be completed."}}), 500

    low, high = models.price_range(price)
    asking_check = None
    asking = summary["asking_price"]
    if asking is not None:
        difference = (asking - price) / price * 100
        position = "below" if asking < low else "above" if asking > high else "within"
        asking_check = {"asking_price": asking, "difference_pct": round(difference, 1), "position": position}

    return jsonify({
        "success": True,
        "vehicle": f"{summary['prod_year']} {summary['manufacturer']}",
        "prediction": {
            "price_usd": round(price, 2),
            "range_low": round(low, 2),
            "range_high": round(high, 2),
            "range_coverage": models.metrics["interval"]["coverage"],
            "model": selected,
            "model_name": MODEL_LABELS[selected],
        },
        "asking_price_check": asking_check,
        "model_comparison": comparison,
        "notices": notices,
    })


@app.errorhandler(404)
def not_found(_):
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "errors": {"_form": "Endpoint not found."}}), 404
    return render_template("index.html", contact_email="", has_video=False), 404


@app.errorhandler(405)
def not_allowed(_):
    return jsonify({"success": False, "errors": {"_form": "Method not allowed."}}), 405


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=False)
