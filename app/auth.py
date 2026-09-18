import os
import secrets
import time

import bcrypt
from fastapi import HTTPException, Request

SESSION_MAX_AGE_SECONDS = 12 * 60 * 60

_RATE_LIMIT_WINDOW = 5 * 60
_RATE_LIMIT_MAX_ATTEMPTS = 8
_failed_attempts: dict[str, list[float]] = {}


def verify_password(plain_password: str) -> bool:
    password_hash = os.environ.get("ADMIN_PASSWORD_HASH", "")
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8")[:72], password_hash.encode("utf-8"))
    except ValueError:
        return False


def is_rate_limited(client_ip: str) -> bool:
    now = time.monotonic()
    attempts = [t for t in _failed_attempts.get(client_ip, []) if now - t < _RATE_LIMIT_WINDOW]
    _failed_attempts[client_ip] = attempts
    return len(attempts) >= _RATE_LIMIT_MAX_ATTEMPTS


def record_failed_attempt(client_ip: str) -> None:
    _failed_attempts.setdefault(client_ip, []).append(time.monotonic())


def clear_failed_attempts(client_ip: str) -> None:
    _failed_attempts.pop(client_ip, None)


def log_in(request: Request) -> None:
    request.session.clear()
    request.session["authenticated"] = True
    request.session["logged_in_at"] = time.time()
    request.session["csrf"] = secrets.token_urlsafe(32)


def log_out(request: Request) -> None:
    request.session.clear()


def is_authenticated(request: Request) -> bool:
    if not request.session.get("authenticated"):
        return False
    logged_in_at = request.session.get("logged_in_at", 0)
    if time.time() - logged_in_at > SESSION_MAX_AGE_SECONDS:
        request.session.clear()
        return False
    return True


def csrf_token(request: Request) -> str:
    return request.session.get("csrf", "")


def check_csrf(request: Request, submitted_token: str) -> None:
    expected = request.session.get("csrf")
    if not expected or not secrets.compare_digest(expected, submitted_token or ""):
        raise HTTPException(status_code=403, detail="bad csrf token")


def require_admin_page(request: Request) -> None:
    if not is_authenticated(request):
        raise HTTPException(status_code=303, headers={"Location": "/login"})


def require_admin_api(request: Request) -> None:
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="not authenticated")
