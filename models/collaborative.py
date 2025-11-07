# models/collaborative.py
import joblib
import pandas as pd
import numpy as np

MODEL_PATH = "data/processed/svd_model.pkl"
MEALS_PATH = "data/processed/meals.csv"

svd = joblib.load(MODEL_PATH)
meals_df = pd.read_csv(MEALS_PATH)

def recommend_for_user(user_id, top_k=5):
    # Dummy – returns random high‑rated meals
    return meals_df.sample(top_k)[['food_id', 'food_name', 'Energy (KCAL)']].to_dict('records')