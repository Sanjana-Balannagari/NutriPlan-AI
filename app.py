# app.py
from flask import Flask, render_template, request, jsonify, send_file
from models.recommender import get_meal_plan
from models.openai_parser import parse_query
from utils.pdf_generator import generate_pdf

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    query = data.get("query", "")
    calories = int(data.get("calories", 2000))
    prefs = [p.strip() for p in data.get("prefs", "").split(",") if p.strip()]

    # Use parser (OpenAI or fallback)
    if query:
        cal, tags = parse_query(query)
        calories = cal
        prefs.extend(tags)

    plan, _ = get_meal_plan(prefs, calories, k=3)
    total = sum(m['calories'] for m in plan if m['id'] != 'N/A')
    for m in plan:
        m['total_calories'] = total
    return jsonify(plan)

@app.route("/export_pdf", methods=["POST"])
def export_pdf():
    plan = request.get_json() or []
    pdf = generate_pdf(plan)
    return send_file(pdf, as_attachment=True, download_name="meal_plan.pdf", mimetype="application/pdf")

if __name__ == "__main__":
    app.run(debug=True)