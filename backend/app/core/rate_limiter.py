# backend/app/core/rate_limiter.py

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse


def get_rate_limit_key(request: Request) -> str:
    """
    Use IP + user_id (if authenticated) as rate limit key.
    Falls back to IP only for unauthenticated requests.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    ip = forwarded.split(",")[0].strip() if forwarded else get_remote_address(request)

    # Try to get user from request state (set by auth middleware)
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"{ip}:{user_id}"
    return ip


limiter = Limiter(key_func=get_rate_limit_key)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Custom handler for rate limit errors — returns JSON with Retry-After."""
    retry_after = 60
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "detail": str(exc.detail),
            "retry_after": retry_after,
        },
        headers={"Retry-After": str(retry_after)},
    )