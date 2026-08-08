from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db
from models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/signup", methods=["GET"])
def signup_page():
    if current_user.is_authenticated:
        return redirect(url_for("chat.index"))
    return render_template("signup.html")

@auth_bp.route("/signup", methods=["POST"])
def signup():
    from config import ALLOWED_EMAILS

    data = request.get_json(silent=True) or request.form

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if len(username) < 3 or len(username) > 32:
        return jsonify({"error": "Username must be between 3 and 32 characters."}), 400

    if "@" not in email or "." not in email.split("@")[-1]:
        return jsonify({"error": "Enter a valid email address."}), 400

    if ALLOWED_EMAILS and email not in ALLOWED_EMAILS:
        return jsonify({"error": "Signups are currently invite-only."}), 403

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username is already taken."}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email is already registered."}), 400

    user = User(username=username, email=email)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    login_user(user, remember=True)

    return jsonify({"success": True, "redirect": url_for("chat.index")})


@auth_bp.route("/login", methods=["GET"])
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("chat.index"))
    return render_template("login.html")


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or request.form

    identifier = (data.get("identifier") or data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter(
        (User.email == identifier) | (User.username == identifier)
    ).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials."}), 401

    login_user(user, remember=True)

    return jsonify({"success": True, "redirect": url_for("chat.index")})


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"success": True, "redirect": url_for("auth.login")})
