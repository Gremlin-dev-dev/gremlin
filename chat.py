
import os
import uuid
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user

from extensions import db
from models import Conversation, Message
from gemini import ask_gemini

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/")
@login_required
def index():
    return render_template("index.html", username=current_user.username)


@chat_bp.route("/api/conversations", methods=["GET"])
@login_required
def list_conversations():
    conversations = (
        Conversation.query.filter_by(user_id=current_user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return jsonify([c.to_dict() for c in conversations])


@chat_bp.route("/api/conversations/<int:conv_id>", methods=["GET"])
@login_required
def get_conversation(conv_id):
    conversation = Conversation.query.filter_by(
        id=conv_id, user_id=current_user.id
    ).first()

    if not conversation:
        return jsonify({"error": "Conversation not found."}), 404

    return jsonify({
        "id": conversation.id,
        "title": conversation.title,
        "messages": [m.to_dict() for m in conversation.messages],

@chat_bp.route("/api/conversations/<int:conv_id>", methods=["PATCH"])
@login_required
def rename_conversation(conv_id):
    conversation = Conversation.query.filter_by(
        id=conv_id, user_id=current_user.id
    ).first()

    if not conversation:
        return jsonify({"error": "Conversation not found."}), 404

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()

    if not title:
        return jsonify({"error": "Title cannot be empty."}), 400

    if len(title) > 120:
        title = title[:120]

    conversation.title = title
    db.session.commit()

    return jsonify(conversation.to_dict())


def _save_image(file_storage):
    if not file_storage or not file_storage.filename:
        return None, None, None

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)

    ext = os.path.splitext(file_storage.filename)[1] or ".png"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(upload_folder, filename)

    image_bytes = file_storage.read()
    mime = file_storage.mimetype or "image/png"

    with open(filepath, "wb") as f:
        f.write(image_bytes)

    relative_path = f"/static/uploads/{filename}"

    return relative_path, image_bytes, mime


@chat_bp.route("/chat", methods=["POST"])
@login_required
def chat():
    message = (request.form.get("message") or "").strip()
    conv_id = request.form.get("conversation_id")
    image_file = request.files.get("image")

    if not message and not image_file:
        return jsonify({"error": "Message or image is required."}), 400

    conversation = None
    if conv_id:
        conversation = Conversation.query.filter_by(
            id=conv_id, user_id=current_user.id
        ).first()

    if not conversation:
        title = message[:40] + ("..." if len(message) > 40 else "") if message else "New chat"
        conversation = Conversation(user_id=current_user.id, title=title or "New chat")
        db.session.add(conversation)
        db.session.commit()

    image_path, image_bytes, image_mime = _save_image(image_file)

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        text=message,
        image_path=image_path,
    )
    db.session.add(user_message)
    db.session.commit()

    history = [
        {"role": m.role, "text": m.text}
        for m in Message.query.filter_by(conversation_id=conversation.id)
        .order_by(Message.created_at)
        .all()
        if m.text
    ]

    reply = ask_gemini(history, image_bytes=image_bytes, image_mime=image_mime)

    bot_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        text=reply,
    )
    db.session.add(bot_message)

    conversation.updated_at = datetime.utcnow()

    db.session.commit()

    return jsonify({
        "reply": reply,
        "conversation_id": conversation.id,
        "title": conversation.title,
    })
