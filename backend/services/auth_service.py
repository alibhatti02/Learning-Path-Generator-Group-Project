import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.database import get_db

# If JWT_SECRET isn't set we fall back to a random per-boot secret: still secure,
# but every restart logs everyone out — set it in .env for real deployments.
JWT_SECRET = os.getenv("JWT_SECRET") or secrets.token_hex(32)
if not os.getenv("JWT_SECRET"):
    print("⚠️ WARNING: JWT_SECRET not set — using an ephemeral secret (tokens die on restart).")

JWT_ALGORITHM = "HS256"
TOKEN_TTL_HOURS = int(os.getenv("TOKEN_TTL_HOURS", "24"))

_bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """One-way bcrypt hash — the plaintext password is never stored and cannot be recovered."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: int, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def register_user(email: str, password: str) -> dict:
    """Creates a user row. Raises ValueError if the email is already taken."""
    with get_db() as conn:
        try:
            cursor = conn.execute(
                "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                (email.strip().lower(), hash_password(password)),
            )
        except sqlite3.IntegrityError:
            raise ValueError("An account with this email already exists.")
        return {"id": cursor.lastrowid, "email": email.strip().lower()}


def authenticate_user(email: str, password: str) -> Optional[dict]:
    """Returns the user on valid credentials, None otherwise (caller decides the error message)."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()

    if row is None or not verify_password(password, row["password_hash"]):
        return None
    return {"id": row["id"], "email": row["email"]}


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> dict:
    """FastAPI dependency: validates the Bearer token and returns {id, email} or raises 401."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated. Please log in.")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid authentication token.")

    return {"id": int(payload["sub"]), "email": payload["email"]}
