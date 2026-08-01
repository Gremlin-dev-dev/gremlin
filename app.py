from flask import Flask, render_template, request, jsonify
from gemini import ask_gemini
import json

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    # Conversation history
    history = json.loads(request.form.get("history", "[]"))

    # Optional uploaded image
    image = request.files.get("image")

    # Ask GREMLIN
    answer = ask_gemini(history, image)

    return jsonify({"reply": answer})


if __name__ == "__main__":
    app.run(debug=True)
