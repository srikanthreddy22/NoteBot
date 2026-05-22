from flask import Blueprint, request, jsonify
from ..services.quiz_gen import generate_quiz

bp = Blueprint("quiz", __name__)

@bp.route("/quiz/", methods=["POST"])
def quiz_route():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400

    count = min(int(data.get("count", 5)), 15)
    try:
        questions = generate_quiz(text, count=count)
        return jsonify({"questions": questions, "count": len(questions)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
