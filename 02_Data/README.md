# 02 - Data

| File | Made in | Content |
| --- | --- | --- |
| `raw_car_price_prediction.csv` | Stage 2 | Original dataset, 19,237 rows x 18 columns (Kaggle: Car Price Prediction Challenge) |
| `train_processed.csv`, `test_processed.csv` | Stage 4 | Processed training (11,208 cars) and test (2,803 cars) data: 57 features + target columns |
| `preprocessing_pipeline.joblib` | Stage 4 | Fitted scikit-learn `ColumnTransformer` (scaling + one-hot encoding), fitted on the training split only |
| `levy_imputation_medians.json` | Stage 4 | Customs-levy medians used to fill a missing levy |
| `preprocessing_metadata.json` | Stage 4 | Feature names, shapes and the leakage safeguards |
| `vehicle_options.json` | Stage 9 | Manufacturer and colour lists for the website drop-downs (`04_Stage_9_Backend/scripts/build_options.py`) |

The notebook `../01_Stages_1_to_8/Stages_1_to_8.ipynb` recreates the Stage 4 files.
