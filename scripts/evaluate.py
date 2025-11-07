# scripts/evaluate.py
import sys
import os

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.recommender import get_meal_plan, precision_at_k

GROUND_TRUTH = {
    "vegan_1800":                ["319874", "1234567", "987654"],
    "lowcarb_highprotein_2200": ["112233", "445566", "778899"],
    "default_1500":              ["223344", "556677", "889900"]
}

def run_tests():
    cases = [
        (["vegan"],                     1800, "vegan_1800"),
        (["low_carb", "high_protein"], 2200, "lowcarb_highprotein_2200"),
        ([],                           1500, "default_1500")
    ]

    print("Running Evaluation\n" + "="*50)
    for prefs, cal, key in cases:
        _, ids = get_meal_plan(prefs, cal, k=5)
        ids = [i for i in ids if i != 'N/A']
        p5 = precision_at_k(ids, GROUND_TRUTH[key], k=5)
        print(f"prefs={prefs} cal={cal} → Precision@5 = {p5:.3f}")

if __name__ == "__main__":
    run_tests()