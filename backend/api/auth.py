"""
api/auth.py — User management and authentication.

- SQLite for user storage (no external DB required)
- JWT tokens via flask-jwt-extended
- First registered user automatically becomes superadmin
- Admin endpoints: list users, update roles
"""
import sqlite3, uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity, get_jwt,
)
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "users.db"

auth_bp = Blueprint("auth", __name__)


# ── Database helpers ──────────────────────────────────────────────────────────

def get_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          TEXT PRIMARY KEY,
                email       TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name        TEXT,
                role        TEXT NOT NULL DEFAULT 'user',
                created_at  TEXT NOT NULL,
                last_login  TEXT
            )
        """)
        conn.commit()


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

    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        role  = "admin" if count == 0 else "user"
        uid   = str(uuid.uuid4())
        try:
            conn.execute(
                "INSERT INTO users (id, email, password_hash, name, role, created_at) VALUES (?,?,?,?,?,?)",
                (uid, email, generate_password_hash(password), name, role,
                 datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        except sqlite3.IntegrityError:
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

    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    with get_db() as conn:
        conn.execute("UPDATE users SET last_login=? WHERE id=?",
                     (datetime.now(timezone.utc).isoformat(), user["id"]))
        conn.commit()

    token = create_access_token(
        identity=user["id"],
        additional_claims={"role": user["role"], "email": user["email"], "name": user["name"]},
    )
    return jsonify({"token": token, "role": user["role"], "email": user["email"], "name": user["name"]})


@auth_bp.get("/api/auth/me")
@jwt_required()
def me():
    uid = get_jwt_identity()
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        "id":         user["id"],
        "email":      user["email"],
        "name":       user["name"],
        "role":       user["role"],
        "created_at": user["created_at"],
        "last_login": user["last_login"],
    })


# ── Admin routes ──────────────────────────────────────────────────────────────

def _require_admin():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403
    return None


@auth_bp.get("/api/admin/users")
@jwt_required()
def list_users():
    if (err := _require_admin()):
        return err
    with get_db() as conn:
        users = conn.execute(
            "SELECT id, email, name, role, created_at, last_login FROM users ORDER BY created_at DESC"
        ).fetchall()
    return jsonify([dict(u) for u in users])


@auth_bp.patch("/api/admin/users/<uid>/role")
@jwt_required()
def update_role(uid):
    if (err := _require_admin()):
        return err
    new_role = (request.get_json() or {}).get("role")
    if new_role not in ("user", "admin"):
        return jsonify({"error": "Role must be 'user' or 'admin'"}), 400
    caller_id = get_jwt_identity()
    if caller_id == uid:
        return jsonify({"error": "Cannot change your own role"}), 400
    with get_db() as conn:
        conn.execute("UPDATE users SET role=? WHERE id=?", (new_role, uid))
        conn.commit()
    return jsonify({"success": True, "role": new_role})


@auth_bp.delete("/api/admin/users/<uid>")
@jwt_required()
def delete_user(uid):
    if (err := _require_admin()):
        return err
    caller_id = get_jwt_identity()
    if caller_id == uid:
        return jsonify({"error": "Cannot delete your own account"}), 400
    with get_db() as conn:
        conn.execute("DELETE FROM users WHERE id=?", (uid,))
        conn.commit()
    return jsonify({"success": True})
