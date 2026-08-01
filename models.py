from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    chats = db.relationship(
        "Chat", backref="user", cascade="all, delete-orphan"
    )


class Chat(db.Model):
    __tablename__ = "chats"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(120), default="New chat")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    messages = db.relationship(
        "Message",
        backref="chat",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey("chats.id"), nullable=False)
    role = db.Column(db.String(20), nullable=False)   # "user" or "assistant"
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
