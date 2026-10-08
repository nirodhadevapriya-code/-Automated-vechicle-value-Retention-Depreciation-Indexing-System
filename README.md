# Used Car Price Prediction - IT3051 Mini Project 2026 (Group KND_11)

Regression system that estimates the market price (USD) of a used car from its specifications.
Dataset: Car Price Prediction (Kaggle, Georgian car listings), 19,237 records, target = `Price`.

## Team (Group KND_11)

| Member | Registration no. |
| --- | --- |
| N S Devapriya (Nirodha) | IT23557956 |
| W G B S Wijerathna | IT23630734 |
| R A N K Ranasinghe | IT23780088 |
| T M A R Gunasekara | IT23614208 |

## Run the system

```bash
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000. Run the tests with `python -m unittest discover -s tests -v`.

## Folder layout

| Path | Stage | Content |
| --- | --- | --- |
| `data/raw_car_price_prediction.csv` | 2 | Original dataset |
| `source_stages_1_to_8/stages_1_to_5_eda_and_preprocessing.ipynb` | 3-4 | EDA, cleaning, feature engineering, train/test split, fitted pipeline |
| `data/train_processed.csv`, `data/test_processed.csv`, `data/preprocessing_pipeline.joblib` | 4 | Processed splits and the fitted preprocessing pipeline |
| `scripts/stage7_tuning.py` | 6-7 | Four baseline models, cross-validation, hyperparameter search, final model selection |
| `data/tuning_results.json`, `models/*.joblib` | 6-7 | Search results and trained models |
| `scripts/build_options.py`, `scripts/build_metrics.py` | 9 | Build the dropdown values and the evaluation numbers used by the app |
| `backend/` | 9 | Input validation, preprocessing, model loading and prediction |
| `app.py` | 9-10 | Flask service (`/api/predict`, `/api/options`, `/api/models`, `/api/health`) and page |
| `templates/index.html`, `static/css`, `static/js` (`site.js`, `app.js`, `cars.js`), `static/vendor`, `static/fonts` | 10 | Website: animated home, analysis charts, cars, estimator, models, presentation deck, contact, footer |
| `scripts/build_insights.py`, `data/insights.json` | 10 | Numbers behind the website's charts and slides |
| `tests/test_api.py` | 9-10 | Automated tests |
| `scripts/ablation_experiments.py`, `scripts/check_serving_consistency.py` | 7, 9 | Feature/target experiments; check that the app reproduces the training pipeline's predictions |
| `report/` | 11 | Technical report (`.docx`, `.pdf`), its figures and `make_figures.py` |
| `presentation/` | 12 | PowerPoint deck with speaker notes and the presenter guide |

## Re-creating the models

```bash
python scripts/stage7_tuning.py     # about 5 minutes
python scripts/build_metrics.py
```

## Notes on use

- The model was trained on listings with production years 1980-2020, so the form accepts only that range.
- `Age` is calculated as 2026 minus the production year, the same as during training.
- The price range shown is the range containing the real price for 80% of the 2,803 test cars; it is not a guarantee.

## Website options

- Put a video at `static/media/hero.mp4` to show it behind the home section (the animation is the default).
- Set the environment variable `CONTACT_EMAIL` before `python app.py` to fill in the recipient of the contact form.
- Rebuild the chart data after retraining with `python scripts/build_insights.py`.
