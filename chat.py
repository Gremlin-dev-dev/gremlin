import os
import json
import uuid
import mimetypes
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify, current_app, Response, stream_with_context
from flask_login import login_required, current_user

from extensions import db
from models import Conversation, Message
from gemini import ask_gemini, ask_gemini_stream

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


def _load_image_from_path(relative_path):
    if not relative_path:
        return None, None

    try:
        filename = os.path.basename(relative_path)
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        filepath = os.path.join(upload_folder, filename)

        with open(filepath, "rb") as f:
            image_bytes = f.read()

        mime = mimetypes.guess_type(filepath)[0] or "image/png"

        return image_bytes, mime

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


@chat_bp.route("/chat/stream", methods=["POST"])
@login_required
def chat_stream():
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

    conv_id_final = conversation.id
    conv_title = conversation.title

    def generate():
        full_reply = ""

        for chunk in ask_gemini_stream(history, image_bytes=image_bytes, image_mime=image_mime):
            full_reply += chunk
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"

        bot_message = Message(
            conversation_id=conv_id_final,
            role="assistant",
            text=full_reply,
        )
        db.session.add(bot_message)

        conv = Conversation.query.get(conv_id_final)
        if conv:
            conv.updated_at = datetime.utcnow()

        db.session.commit()

        yield f"data: {json.dumps({'done': True, 'conversation_id': conv_id_final, 'title': conv_title})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


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
