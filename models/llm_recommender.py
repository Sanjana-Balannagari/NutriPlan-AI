# models/llm_recommender.py
import json
import random
import logging
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd
import openai

# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------
DATA_PATH = Path("data") / "processed" / "meals.csv"

if not DATA_PATH.exists():
    raise FileNotFoundError(f"meals.csv not found at {DATA_PATH.resolve()}")

print(f"[OK] Found CSV: {DATA_PATH.resolve()}")

logger = logging.getLogger(__name__)

# Load and clean data
df = pd.read_csv(DATA_PATH)
df = df.rename(columns={"Energy (KCAL)": "calories"})
df["calories"] = pd.to_numeric(df["calories"], errors="coerce")
df = df.dropna(subset=["calories", "food_id", "meal_type"]).copy()
df["meal_type"] = df["meal_type"].str.lower()

_MEALS_DF = df

def _sample_options(meal_type: str, max_calories: int, n: int = 5) -> List[Dict]:
    subset = _MEALS_DF[
        (_MEALS_DF["meal_type"] == meal_type.lower()) &
        (_MEALS_DF["calories"] <= max_calories)
    ]
    if len(subset) == 0:
        # Fallback: ignore calorie limit if nothing fits
        subset = _MEALS_DF[_MEALS_DF["meal_type"] == meal_type.lower()]
    return subset.sample(n=min(n, len(subset)), replace=False).to_dict(orient="records")

def _call_llm_for_meal(meal_type: str, user_query: str, max_calories: int) -> Dict[str, Any]:
    options = _sample_options(meal_type, max_calories)

    prompt = f"""
YOU ARE A STRICT MEAL PLANNER.
Target calories: ~{max_calories} kcal (do not go much lower unless impossible).
User preferences: {user_query}

CRITICAL:
- If "beef" is mentioned, the meal MUST contain beef.
- Pick a meal close to {max_calories} kcal, not the lowest one.
- Never pick chicken if beef is requested.

Return ONLY JSON:
{{
  "name": "...",
  "calories": {max_calories - 100} to {max_calories + 100},
  "food_id": "...",
  "reason": "1 short sentence"
}}

Options:
{json.dumps(options, indent=2)}
"""

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=300,
        )
        raw = response.choices[0].message.content.strip()
        logger.info(f"LLM {meal_type} (≤{max_calories} cal): {raw}")
        meal = json.loads(raw)

        # FINAL SAFETY: Force calorie respect
        chosen_cal = int(meal.get("calories", 0))
        if chosen_cal > max_calories:
            logger.warning(f"LLM ignored limit ({chosen_cal} > {max_calories}), picking safest option")
            safe = min(options, key=lambda x: x["calories"])
            return {
                "name": safe["food_name"],
                "calories": int(safe["calories"]),
                "food_id": safe["food_id"],
                "reason": "Enforced calorie limit"
            }

        return {
            "name": meal.get("name", "Unknown Meal"),
            "calories": chosen_cal,
            "food_id": meal.get("food_id", "N/A"),
            "reason": meal.get("reason", "Selected by AI")
        }

    except Exception as e:
        logger.error(f"LLM failed for {meal_type}: {e}")
        # Ultimate fallback
        safe = min(options, key=lambda x: x["calories"]) if options else {"food_name": "Basic Meal", "calories": 300, "food_id": "fallback"}
        return {
            "name": safe.get("food_name", "Basic Meal"),
            "calories": min(int(safe.get("calories", 300)), max_calories),
            "food_id": safe.get("food_id", "N/A"),
            "reason": "Fallback due to error"
        }

def get_llm_meal_plan(query: str, total_calories: int) -> Dict[str, Any]:
    total_calories = max(total_calories, 900)  # minimum realistic
    query_lower = query.lower()

    # Detect if user wants specific ingredient in lunch
    wants_beef_lunch = "beef" in query_lower and ("lunch" in query_lower or "meal" in query_lower or "dinner" not in query_lower)

    # Force calorie distribution
    target = total_calories // 3

    # Breakfast: normal
    breakfast = _call_llm_for_meal("breakfast", query, target + 100)

    # Lunch: special handling if beef requested
    if wants_beef_lunch:
        lunch = _call_llm_for_meal("lunch", query + " MUST INCLUDE BEEF, around 600-750 kcal", 800)
    else:
        lunch = _call_llm_for_meal("lunch", query, target + 50)

    # Dinner gets the rest to hit total
    remaining = total_calories - breakfast["calories"] - lunch["calories"]
    dinner = _call_llm_for_meal("dinner", query, max(400, remaining))

    total = breakfast["calories"] + lunch["calories"] + dinner["calories"]

    return {
        "breakfast": breakfast,
        "lunch": lunch,
        "dinner": dinner,
        "total_calories": min(total, total_calories),  # never over
        "query": query,
    }