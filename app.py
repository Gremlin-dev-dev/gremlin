from flask import Flask, render_template, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from config import SECRET_KEY
from gemini import ask_gemini
from models import db, User
import json

app = Flask(__name__)
app.secret_key = SECRET_KEY
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


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    user = User.query.filter_by(username=username).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "invalid username or password"}), 401

    session["user_id"] = user.id

    return jsonify({"message": "logged in", "username": user.username}), 200


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "logged out"}), 200


@app.route("/me")
def me():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({"logged_in": False}), 200

    user = db.session.get(User, user_id)
    return jsonify({"logged_in": True, "username": user.username}), 200


if __name__ == "__main__":
    app.run(debug=True)
