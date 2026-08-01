from flask import session
from werkzeug.security import check_password_hash
from config import SECRET_KEY
from flask import Flask, render_template, request, jsonify
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import IntegrityError
from gemini import ask_gemini
from models import db, User
import json

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///gremlin.db"
db.init_app(app)

with app.app_context():
    db.create_all()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    history = json.loads(request.form.get("history", "[]"))
    image = request.files.get("image")
    answer = ask_gemini(history, image)
    return jsonify({"reply": answer})


@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True) or {}

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not (3 <= len(username) <= 30):
        return jsonify({"error": "username must be 3-30 characters"}), 400

    if not (8 <= len(password) <= 128):
        return jsonify({"error": "password must be 8-128 characters"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "username already taken"}), 409

    user = User(
        username=username,
        password_hash=generate_password_hash(password),
    )
    db.session.add(user)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "username already taken"}), 409

    return jsonify({"message": "account created"}), 201


if __name__ == "__main__":
    app.run(debug=True)
