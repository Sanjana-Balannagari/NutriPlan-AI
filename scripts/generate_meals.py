# scripts/generate_meals.py
import pandas as pd
import os
import numpy as np
import sys

# ----------------------------------------------------------------------
# Make imports work when the script is run from the project root
# ----------------------------------------------------------------------
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ----------------------------------------------------------------------
# INPUT / OUTPUT
# ----------------------------------------------------------------------
FOOD_PATH       = "data/raw/food.csv"
NUTRIENT_PATH   = "data/raw/food_nutrient.csv"
NUTRIENT_DEF    = "data/raw/nutrient.csv"
OUT_PATH        = "data/processed/meals.csv"

os.makedirs("data/processed", exist_ok=True)

# ----------------------------------------------------------------------
# 1. Load nutrient definitions → keep only Energy (KCAL)
# ----------------------------------------------------------------------
print("Loading nutrient definitions...")
nutrient_def = pd.read_csv(NUTRIENT_DEF)

ENERGY_IDS = nutrient_def[
    nutrient_def["name"].str.contains("Energy", case=False, na=False)
]["id"].tolist()

print(f"Found {len(ENERGY_IDS)} energy nutrients: {ENERGY_IDS}")

# ----------------------------------------------------------------------
# 2. Load food.csv (small)
# ----------------------------------------------------------------------
print("Loading food.csv...")
food_df = pd.read_csv(FOOD_PATH)
food_df = food_df[["fdc_id", "description", "food_category_id"]].copy()
food_df = food_df.rename(columns={"fdc_id": "food_id", "description": "food_name"})

# ----------------------------------------------------------------------
# 3. Stream food_nutrient.csv → keep only energy rows
# ----------------------------------------------------------------------
print("Streaming food_nutrient.csv (only energy rows)...")
chunksize = 500_000
energy_chunks = []

for chunk in pd.read_csv(NUTRIENT_PATH, chunksize=chunksize, low_memory=False):
    energy_chunk = chunk[chunk["nutrient_id"].isin(ENERGY_IDS)]
    if not energy_chunk.empty:
        energy_chunks.append(energy_chunk[["fdc_id", "nutrient_id", "amount"]])

if not energy_chunks:
    raise ValueError("No energy data found! Check nutrient.csv IDs.")

energy_df = pd.concat(energy_chunks, ignore_index=True)
print(f"   → {len(energy_df):,} energy rows kept")

# ----------------------------------------------------------------------
# 4. Pivot: one row per food_id with energy values
# ----------------------------------------------------------------------
print("Pivoting energy data...")
energy_pivot = energy_df.pivot_table(
    index="fdc_id",
    columns="nutrient_id",
    values="amount",
    aggfunc="first"
).reset_index()

# Flatten column names
energy_pivot.columns = [
    f"energy_{int(c)}" if isinstance(c, (int, float)) else c for c in energy_pivot.columns
]

# ----------------------------------------------------------------------
# 5. Merge with food
# ----------------------------------------------------------------------
print("Merging with food data...")
meals = food_df.merge(energy_pivot, left_on="food_id", right_on="fdc_id", how="left")
meals = meals.drop(columns=["fdc_id"], errors="ignore")

# Pick first non-null energy column
energy_cols = [c for c in meals.columns if c.startswith("energy_")]
meals["Energy (KCAL)"] = meals[energy_cols].bfill(axis=1).iloc[:, 0]

# Drop rows without calories
meals = meals.dropna(subset=["Energy (KCAL)"])
meals["Energy (KCAL)"] = meals["Energy (KCAL)"].astype(int)

# ----------------------------------------------------------------------
# 6. Add meal_type & tags
# ----------------------------------------------------------------------
meals["meal_type"] = np.random.choice(["Breakfast", "Lunch", "Dinner"], size=len(meals))

def derive_tags(row):
    tags = set()
    desc = str(row["food_name"]).lower()
    cat  = str(row.get("food_category_id", "")).lower()
    if any(w in desc for w in ["vegan", "plant"]):      tags.add("vegan")
    if any(w in desc for w in ["low carb", "keto"]):    tags.add("low_carb")
    if any(w in desc for w in ["protein", "chicken", "beef"]): tags.add("high_protein")
    if any(w in desc for w in ["healthy", "organic"]):  tags.add("healthy")
    if any(w in desc for w in ["lunch", "sandwich"]):   tags.add("lunch")
    return ",".join(tags)

meals["tags"] = meals.apply(derive_tags, axis=1)

# ----------------------------------------------------------------------
# 7. NEW: Classify food_type (solid vs beverage)
# ----------------------------------------------------------------------
def is_real_meal(row):
    desc = str(row["food_name"]).lower()
    # Exclude snacks, chips, nuts, bars, seeds
    snack_keywords = [
        "chip", "chips", "bar", "bars", "nut", "nuts", "seed", "seeds",
        "crisp", "crisps", "snack", "snacks", "bite", "bites", "mix",
        "popcorn", "pretzel", "cracker", "puff", "puffs", "jerky"
    ]
    if any(k in desc for k in snack_keywords):
        return "no"
    return "yes"
def calorie_check(row, meal_type):
    cal = row["Energy (KCAL)"]
    if meal_type == "Breakfast":
        return 300 <= cal <= 700
    elif meal_type == "Lunch":
        return 500 <= cal <= 900
    elif meal_type == "Dinner":
        return 500 <= cal <= 900
    return False
def is_main_dish(row):
    desc = str(row["food_name"]).lower()
    # Exclude condiments, sauces, spreads, dips
    condiment_keywords = [
        "sauce", "dressing", "marinade", "dip", "spread", "butter",
        "cream", "cheese", "mayo", "ketchup", "mustard", "relish",
        "pesto", "aioli", "hummus", "guacamole", "salsa"
    ]
    if any(k in desc for k in condiment_keywords):
        return "no"
    return "yes"
def is_snack(row):
    desc = str(row["food_name"]).lower()
    snack_keywords = [
        "granola", "oil", "blend", "strip", "strips", "chip", "chips",
        "bar", "bars", "crunch", "snaps", "bites", "mix", "puffs",
        "crackers", "popcorn", "pretzel", "jerky", "trail", "energy"
    ]
    if any(k in desc for k in snack_keywords):
        return "yes"
    return "no"
def classify_food(row):
    desc = str(row["food_name"]).lower()
    # Add more beverage keywords if you discover them
    beverage_keywords = [
        "juice", "drink", "beverage", "soda", "water", "tea", "coffee",
        "milk", "shake", "smoothie", "cocoa", "broth", "soup"
    ]
    if any(k in desc for k in beverage_keywords):
        return "beverage"
    return "solid"

meals["food_type"] = meals.apply(classify_food, axis=1)
meals["is_meal"] = meals.apply(is_real_meal, axis=1)
meals["is_main_dish"] = meals.apply(is_main_dish, axis=1)
meals["valid_cal"] = meals.apply(
    lambda row: calorie_check(row, row["meal_type"]), axis=1
)
meals["is_snack"] = meals.apply(is_snack, axis=1)
# ----------------------------------------------------------------------
# 8. Inject Ground Truth (all marked as solid)
# ----------------------------------------------------------------------
ground_truth = [
    {"food_id": 319874,  "food_name": "Hummus, Sabra Classic",      "Energy (KCAL)": 720, "meal_type": "Lunch",   "tags": "vegan,healthy,lunch",      "food_type": "solid"},
    {"food_id": 1234567, "food_name": "Healthy Choice Vegan Bowl",  "Energy (KCAL)": 540, "meal_type": "Dinner",  "tags": "vegan,healthy",            "food_type": "solid"},
    {"food_id": 987654,  "food_name": "Tofu Quinoa Salad",         "Energy (KCAL)": 540, "meal_type": "Breakfast","tags": "vegan,high_protein",      "food_type": "solid"},
    {"food_id": 112233,  "food_name": "Grilled Chicken Breast",    "Energy (KCAL)": 880, "meal_type": "Dinner",  "tags": "low_carb,high_protein",   "food_type": "solid"},
    {"food_id": 445566,  "food_name": "Salmon Avocado Bowl",       "Energy (KCAL)": 880, "meal_type": "Lunch",   "tags": "low_carb,high_protein",   "food_type": "solid"},
    {"food_id": 778899,  "food_name": "Egg White Omelette",        "Energy (KCAL)": 660, "meal_type": "Breakfast","tags": "low_carb,high_protein",   "food_type": "solid"},
    {"food_id": 223344,  "food_name": "Greek Yogurt Bowl",         "Energy (KCAL)": 450, "meal_type": "Breakfast","tags": "healthy",                 "food_type": "solid"},
    {"food_id": 556677,  "food_name": "Turkey Sandwich",           "Energy (KCAL)": 600, "meal_type": "Lunch",   "tags": "healthy",                 "food_type": "solid"},
    {"food_id": 889900,  "food_name": "Veggie Stir Fry",           "Energy (KCAL)": 450, "meal_type": "Dinner",  "tags": "healthy",                 "food_type": "solid"},
]

gt_df = pd.DataFrame(ground_truth)

# Ensure food_id is string everywhere
meals["food_id"] = meals["food_id"].astype(str)
gt_df["food_id"]   = gt_df["food_id"].astype(str)

# Remove any accidental duplicates of ground-truth IDs
meals = meals[~meals["food_id"].isin(gt_df["food_id"])]

# Append ground truth
meals = pd.concat([meals, gt_df], ignore_index=True)

# ----------------------------------------------------------------------
# 9. Save final CSV (now includes food_type)
# ----------------------------------------------------------------------
final_cols = [
    "food_id", "food_name", "Energy (KCAL)", "meal_type", "tags",
    "food_type", "is_meal", "is_main_dish", "valid_cal", "is_snack"
]
meals[final_cols].to_csv(OUT_PATH, index=False)

print(f"\nmeals.csv created: {OUT_PATH}")
print(f"   Total meals : {len(meals):,}")
print(f"   Solid foods : {len(meals[meals['food_type'] == 'solid']):,}")
print(f"   Beverages   : {len(meals[meals['food_type'] == 'beverage']):,}")
print(f"   Sample:\n{meals[final_cols].head(3)}")