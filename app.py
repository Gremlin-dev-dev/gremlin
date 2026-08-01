from flask import Flask, render_template, request, jsonify
from gemini import ask_gemini
import json

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


def parse_history(raw_history):
    """
    Parses and validates the history field from the request.
    Returns (history, error_message). error_message is None on success.
    """
    try:
        history = json.loads(raw_history)
    except json.JSONDecodeError:
        return None, "history must be valid JSON"

    if not isinstance(history, list):
        return None, "history must be a list"

    for msg in history:
        if not isinstance(msg, dict):
            return None, "each history entry must be an object"
        if msg.get("role") not in ("user", "assistant"):
            return None, "each history entry needs a valid 'role'"
        if not isinstance(msg.get("text"), str):
            return None, "each history entry needs 'text' as a string"

    return history, None


@app.route("/chat", methods=["POST"])
def chat():
    raw_history = request.form.get("history", "[]")
    history, error = parse_history(raw_history)

    if error:
        return jsonify({"error": error}), 400

    image = request.files.get("image")

    answer = ask_gemini(history, image)

    return jsonify({"reply": answer})


if __name__ == "__main__":
    app.run(debug=True)
