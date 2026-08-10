from functools import wraps
from inspect import iscoroutinefunction

from itsdangerous import BadSignature, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from app.config import SECRET_KEY

serializer = URLSafeTimedSerializer(SECRET_KEY, salt="auth")


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return check_password_hash(password_hash, password)


def create_session_token(user_id: int, username: str, role: str) -> str:
    return serializer.dumps({"uid": user_id, "username": username, "role": role})


def read_session_token(token: str) -> dict | None:
    try:
        return serializer.loads(token, max_age=3600 * 24)
    except (BadSignature, Exception):
        return None


def require_role(*roles: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            session = getattr(getattr(request, "state", None), "session", {}) or {}
            role = session.get("role")
            if not role:
                from fastapi.responses import RedirectResponse

                return RedirectResponse("/login", status_code=303)
            if roles and role not in roles:
                from fastapi.responses import RedirectResponse

                return RedirectResponse("/drafts", status_code=303)
            result = func(request, *args, **kwargs)
            if iscoroutinefunction(func):
                return await result
            return result

        return wrapper

    return decorator
