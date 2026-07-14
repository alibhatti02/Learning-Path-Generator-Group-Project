"""
Central rate-limiting config (slowapi).

Two keying strategies:
  * Auth endpoints are limited by client IP — the caller isn't authenticated yet,
    and the goal is to blunt brute-force / mass-signup attempts.
  * AI endpoints are limited per authenticated user, so one account can't burn
    through the Azure OpenAI / YouTube budget (and so shared-NAT users aren't
    punished for each other). Falls back to IP if there's no valid token.

Storage is in-memory by default, which is per-process — fine for a single
instance. Set RATE_LIMIT_STORAGE_URI (e.g. redis://host:6379) once you run more
than one backend instance so the counters are shared.
"""
import os

import jwt
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from services.auth_service import JWT_ALGORITHM, JWT_SECRET

# Limits are env-overridable so they can be tuned in prod without a code change.
AUTH_REGISTER_LIMIT = os.getenv("RL_REGISTER", "5/hour")
AUTH_LOGIN_LIMIT = os.getenv("RL_LOGIN", "10/minute")
AI_ROADMAP_LIMIT = os.getenv("RL_ROADMAP", "15/hour")
AI_QUIZ_GEN_LIMIT = os.getenv("RL_QUIZ_GEN", "40/hour")
AI_QUIZ_SUBMIT_LIMIT = os.getenv("RL_QUIZ_SUBMIT", "40/hour")
AI_RESUME_LIMIT = os.getenv("RL_RESUME", "10/hour")


def _client_ip(request: Request) -> str:
    """Real client IP. Behind Azure's proxy the socket peer is the load balancer,
    so honor the first X-Forwarded-For entry when present."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


def user_or_ip_key(request: Request) -> str:
    """Key AI endpoints per authenticated user; fall back to IP if the token is
    missing/invalid (the endpoint's own auth dependency will reject it anyway)."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            payload = jwt.decode(auth[7:], JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return f"user:{payload['sub']}"
        except jwt.InvalidTokenError:
            pass
    return f"ip:{_client_ip(request)}"


_storage_uri = os.getenv("RATE_LIMIT_STORAGE_URI") or "memory://"
limiter = Limiter(key_func=_client_ip, storage_uri=_storage_uri)
