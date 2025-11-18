# app.py
from flask import Flask, render_template, request, jsonify
import logging

from models.llm_recommender import get_llm_meal_plan

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "No JSON payload"}), 400

        query = data.get("query", "").strip()
        calories = int(data.get("calories", 2000))

        logging.info(f"Request → query: '{query}', calories: {calories}")

        plan = get_llm_meal_plan(query, calories)

        if "error" in plan:
            return jsonify(plan), 500

        return jsonify(plan)

    except Exception as e:
        logging.exception("Server error")
        return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(debug=True)