"""
api/auth.py — User management and authentication.

- MongoDB for persistent user storage (survives Render restarts)
- JWT tokens via flask-jwt-extended
- First registered user automatically becomes superadmin
- Admin endpoints: list users, update roles, delete users
"""
import uuid
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity, get_jwt,
)
from pymongo.errors import DuplicateKeyError
from werkzeug.security import generate_password_hash, check_password_hash

from api.database import get_db

auth_bp = Blueprint("auth", __name__)


def init_db():
    """Create indexes on first startup."""
    get_db().users.create_index("email", unique=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _user_response(doc: dict) -> dict:
    """Strip password hash and normalise _id → id for API responses."""
    return {
        "id":         doc["_id"],
        "email":      doc["email"],
        "name":       doc.get("name", ""),
        "role":       doc["role"],
        "created_at": doc.get("created_at"),
        "last_login": doc.get("last_login"),
    }


# ── Auth routes ───────────────────────────────────────────────────────────────

@auth_bp.post("/api/auth/register")
def register():
    data     = request.get_json() or {}
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")
    name     = data.get("name", "").strip() or email.split("@")[0]

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    db   = get_db()
    role = "admin" if db.users.count_documents({}) == 0 else "user"
    uid  = str(uuid.uuid4())

    try:
        db.users.insert_one({
            "_id":           uid,
            "email":         email,
            "password_hash": generate_password_hash(password),
            "name":          name,
            "role":          role,
            "created_at":    _now(),
            "last_login":    None,
        })
    except DuplicateKeyError:
        return jsonify({"error": "Email already registered"}), 409

    token = create_access_token(
        identity=uid,
        additional_claims={"role": role, "email": email, "name": name},
    )
    return jsonify({"token": token, "role": role, "email": email, "name": name}), 201


@auth_bp.post("/api/auth/login")
def login():
    data     = request.get_json() or {}
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user = get_db().users.find_one({"email": email})
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    get_db().users.update_one({"_id": user["_id"]}, {"$set": {"last_login": _now()}})

    token = create_access_token(
        identity=user["_id"],
        additional_claims={"role": user["role"], "email": user["email"], "name": user.get("name", "")},
    )
    return jsonify({
        "token": token,
        "role":  user["role"],
        "email": user["email"],
        "name":  user.get("name", ""),
    })


@auth_bp.get("/api/auth/me")
@jwt_required()
def me():
    user = get_db().users.find_one({"_id": get_jwt_identity()})
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(_user_response(user))


# ── Admin routes ──────────────────────────────────────────────────────────────

def _require_admin():
    if get_jwt().get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403
    return None


@auth_bp.get("/api/admin/users")
@jwt_required()
def list_users():
    if (err := _require_admin()):
        return err
    users = list(get_db().users.find({}, {"password_hash": 0}).sort("created_at", -1))
    return jsonify([_user_response(u) for u in users])


@auth_bp.patch("/api/admin/users/<uid>/role")
@jwt_required()
def update_role(uid):
    if (err := _require_admin()):
        return err
    new_role = (request.get_json() or {}).get("role")
    if new_role not in ("user", "admin"):
        return jsonify({"error": "Role must be 'user' or 'admin'"}), 400
    if get_jwt_identity() == uid:
        return jsonify({"error": "Cannot change your own role"}), 400
    get_db().users.update_one({"_id": uid}, {"$set": {"role": new_role}})
    return jsonify({"success": True, "role": new_role})


@auth_bp.delete("/api/admin/users/<uid>")
@jwt_required()
def delete_user(uid):
    if (err := _require_admin()):
        return err
    if get_jwt_identity() == uid:
        return jsonify({"error": "Cannot delete your own account"}), 400
    get_db().users.delete_one({"_id": uid})
    return jsonify({"success": True})
