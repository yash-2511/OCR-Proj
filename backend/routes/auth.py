from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from flask import Blueprint, current_app, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from backend.models.database import User, db


auth_bp = Blueprint("auth", __name__)
TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24 * 7
TOKEN_SALT = "ocr-proj-auth-token"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=TOKEN_SALT)


def _issue_token(user: User) -> str:
    return _serializer().dumps({"user_id": user.id})


def _read_bearer_token() -> str | None:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    token = header.split(" ", 1)[1].strip()
    return token or None


def _current_user() -> User | None:
    token = _read_bearer_token()
    if not token:
        return None
    try:
        payload = _serializer().loads(token, max_age=TOKEN_MAX_AGE_SECONDS)
    except SignatureExpired:
        return None
    except BadSignature:
        return None
    user_id = payload.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def auth_required(view: Callable[..., Any]):
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any):
        user = _current_user()
        if user is None:
            return jsonify({"success": False, "data": None, "error": "Authentication required"}), 401
        request.current_user = user  # type: ignore[attr-defined]
        return view(*args, **kwargs)

    return wrapped


@auth_bp.post("/api/auth/signup")
def signup():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    if not name or not email or not password:
        return jsonify({"success": False, "data": None, "error": "Name, email, and password are required"}), 400
    if len(password) < 6:
        return jsonify({"success": False, "data": None, "error": "Password must be at least 6 characters"}), 400
    if User.query.filter_by(email=email).first() is not None:
        return jsonify({"success": False, "data": None, "error": "Email is already registered"}), 409

    user = User(name=name, email=email, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()

    token = _issue_token(user)
    return jsonify({"success": True, "data": {"token": token, "user": user.to_dict()}, "error": None}), 201


@auth_bp.post("/api/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    if not email or not password:
        return jsonify({"success": False, "data": None, "error": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if user is None or not check_password_hash(user.password_hash, password):
        return jsonify({"success": False, "data": None, "error": "Invalid email or password"}), 401

    token = _issue_token(user)
    return jsonify({"success": True, "data": {"token": token, "user": user.to_dict()}, "error": None})


@auth_bp.get("/api/auth/me")
def me():
    user = _current_user()
    if user is None:
        return jsonify({"success": False, "data": None, "error": "Authentication required"}), 401
    return jsonify({"success": True, "data": {"user": user.to_dict()}, "error": None})


@auth_bp.post("/api/auth/logout")
def logout():
    return jsonify({"success": True, "data": {"logged_out": True}, "error": None})
