# scripts/train_cf.py
import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD
import joblib
import os

MEALS_PATH = "data/processed/meals.csv"
MODEL_PATH = "data/processed/svd_model.pkl"

os.makedirs("data/processed", exist_ok=True)

df = pd.read_csv(MEALS_PATH)

# ---- Fake interaction matrix (replace with real ratings later) ----
np.random.seed(42)
n_users = 500
n_items = len(df)
interactions = pd.DataFrame({
    'user_id': np.random.randint(0, n_users, size=5000),
    'food_id': np.random.choice(df['food_id'], size=5000),
    'rating': np.random.randint(1, 6, size=5000)
})

# ---- Build sparse matrix ----
user_map = {uid: i for i, uid in enumerate(interactions['user_id'].unique())}
item_map = {fid: i for i, fid in enumerate(interactions['food_id'].unique())}
row = interactions['user_id'].map(user_map)
col = interactions['food_id'].map(item_map)
data = interactions['rating']

sparse = csr_matrix((data, (row, col)), shape=(len(user_map), len(item_map)))

# ---- Train SVD ----
svd = TruncatedSVD(n_components=50, random_state=42)
svd.fit(sparse)

joblib.dump(svd, MODEL_PATH)
print(f"SVD model saved to {MODEL_PATH}")