import os
import uuid
import requests
import mimetypes
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
    })


@chat_bp.route("/api/conversations/<int:conv_id>", methods=["DELETE"])
@login_required
def delete_conversation(conv_id):
    conversation = Conversation.query.filter_by(
        id=conv_id, user_id=current_user.id
    ).first()

    if not conversation:
        return jsonify({"error": "Conversation not found."}), 404

    db.session.delete(conversation)
    db.session.commit()

    return jsonify({"success": True})


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


import cloudinary.uploader


def _save_image(file_storage):
    if not file_storage or not file_storage.filename:
        return None, None, None

    image_bytes = file_storage.read()
    mime = file_storage.mimetype or "image/png"

    try:
        upload_result = cloudinary.uploader.upload(
            image_bytes,
            folder="gremlin_uploads",
            resource_type="image",
        )
        image_url = upload_result.get("secure_url")
    except Exception:
        image_url = None

    return image_url, image_bytes, mime


def _load_image_from_path(image_url):
    if not image_url:
        return None, None

    try:
        response = requests.get(image_url, timeout=15)
        if response.status_code != 200:
            return None, None

        mime = mimetypes.guess_type(image_url)[0] or "image/png"

        return response.content, mime

    except Exception:
        return None, None

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
][-30:]
    
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


@chat_bp.route("/api/conversations/<int:conv_id>/retry", methods=["POST"])
@login_required
def retry_last_message(conv_id):
    conversation = Conversation.query.filter_by(
        id=conv_id, user_id=current_user.id
    ).first()

    if not conversation:
        return jsonify({"error": "Conversation not found."}), 404

    messages = (
        Message.query.filter_by(conversation_id=conversation.id)
        .order_by(Message.created_at)
        .all()
    )

    if not messages:
        return jsonify({"error": "Nothing to retry."}), 400

    if messages[-1].role == "assistant":
        db.session.delete(messages[-1])
        db.session.commit()
        messages = messages[:-1]

    if not messages or messages[-1].role != "user":
        return jsonify({"error": "No user message to respond to."}), 400

    last_user_message = messages[-1]

    image_bytes, image_mime = _load_image_from_path(last_user_message.image_path)

    history = [
    {"role": m.role, "text": m.text}
    for m in messages
    if m.text
][-30:]
    
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
    })


@chat_bp.route("/api/conversations/<int:conv_id>/edit-last", methods=["POST"])
@login_required
def edit_last_message(conv_id):
    conversation = Conversation.query.filter_by(
        id=conv_id, user_id=current_user.id
    ).first()

    if not conversation:
        return jsonify({"error": "Conversation not found."}), 404

    data = request.get_json(silent=True) or {}
    new_text = (data.get("text") or "").strip()

    if not new_text:
        return jsonify({"error": "Message cannot be empty."}), 400

    messages = (
        Message.query.filter_by(conversation_id=conversation.id)
        .order_by(Message.created_at)
        .all()
    )

    if not messages:
        return jsonify({"error": "Nothing to edit."}), 400

    if messages[-1].role == "assistant":
        db.session.delete(messages[-1])
        db.session.commit()
        messages = messages[:-1]

    if not messages or messages[-1].role != "user":
        return jsonify({"error": "No user message to edit."}), 400

    last_user_message = messages[-1]
    last_user_message.text = new_text
    db.session.commit()

    image_bytes, image_mime = _load_image_from_path(last_user_message.image_path)

    history = [
        {"role": m.role, "text": m.text}
        for m in messages
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
        "edited_text": new_text,
        "conversation_id": conversation.id,
    })
