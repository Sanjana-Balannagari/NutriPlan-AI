# models/openai_parser.py
import re
import os
from dotenv import load_dotenv
load_dotenv()
# Try to get API key
API_KEY = os.getenv("OPENAI_API_KEY")

if API_KEY:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=API_KEY)
        USE_OPENAI = True
        print("OpenAI API key found – using advanced parsing")
    except Exception as e:
        print(f"OpenAI import failed: {e}")
        USE_OPENAI = False
else:
    print("No OPENAI_API_KEY – using fallback parser")
    USE_OPENAI = False

def parse_query(text: str):
    """Parse calories and tags from text."""
    if not text:
        return 2000, []

    # Extract calories
    cal_match = re.search(r'(\d{3,4})\s*cal', text.lower())
    calories = int(cal_match.group(1)) if cal_match else 2000

    # Extract tags
    tags = []
    tag_map = {
        'vegan': 'vegan',
        'low carb': 'low_carb',
        'high protein': 'high_protein',
        'healthy': 'healthy',
        'lunch': 'lunch',
        'breakfast': 'breakfast',
        'dinner': 'dinner'
    }
    text_lower = text.lower()
    for phrase, tag in tag_map.items():
        if phrase in text_lower:
            tags.append(tag)

    return calories, tags