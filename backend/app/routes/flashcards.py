from flask import Blueprint, request, jsonify
from ..services.flashcard_gen import generate_flashcards

bp = Blueprint("flashcards", __name__)

@bp.route("/flashcards/", methods=["POST"])
def flashcards_route():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400

    count = min(int(data.get("count", 8)), 20)
    try:
        cards = generate_flashcards(text, count=count)
        return jsonify({"flashcards": cards, "count": len(cards)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
