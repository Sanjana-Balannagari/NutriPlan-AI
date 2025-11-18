# scripts/generate_meals_llm.py
import os
import json
import time
import re
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
import json_repair

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """Return EXACTLY 30 full meals (breakfast, lunch, dinner). No snacks, desserts, or oils."""
USER_PROMPT = """Generate 30 meals:
- name, calories (300–900), meal_type (Breakfast|Lunch|Dinner)
- tags (comma-separated), ingredients (3–6 items)
Return ONLY a JSON array."""

def call_llm():
    for _ in range(3):
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": SYSTEM_PROMPT},
                          {"role": "user", "content": USER_PROMPT}],
                temperature=0.3,
                max_tokens=3800,
                response_format={"type": "json_object"}
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(2)
    raise RuntimeError("LLM failed")

def parse_meals(raw):
    Path("debug_raw_response.txt").write_text(raw, encoding="utf-8")
    try:
        repaired = json_repair.loads(raw)
        if isinstance(repaired, list): return repaired
    except: pass
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    return json.loads(match.group(0)) if match else []

def main():
    all_meals = []
    for i in range(10):
        print(f"Batch {i+1}/10")
        raw = call_llm()
        batch = parse_meals(raw)
        valid = [m for m in batch if 300 <= m.get("calories", 0) <= 900 and m.get("meal_type") in {"Breakfast","Lunch","Dinner"}]
        if len(valid) >= 20:
            all_meals.extend(valid)
            print(f"Kept {len(valid)}")
        time.sleep(1)

    df = pd.DataFrame(all_meals[:300])
    df = df.rename(columns={"name": "food_name", "calories": "Energy (KCAL)"})
    df["food_id"] = range(1000000, 1000000 + len(df))
    for c, v in [("food_type","solid"), ("is_meal","yes")]: df[c] = v

    os.makedirs("data/processed", exist_ok=True)
    df.to_csv("data/processed/meals.csv", index=False)
    print(f"SUCCESS! Saved {len(df)} meals")

if __name__ == "__main__":
    main()