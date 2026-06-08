import time
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


def get_user_or_ip(request: Request) -> str:
    """Use user ID for authenticated requests, IP for unauthenticated."""
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        token = auth.split(" ")[1]
        # Use first 16 chars of token as key (don't expose full token)
        return f"user:{token[:16]}"
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"apikey:{api_key[:16]}"
    return f"ip:{get_remote_address(request)}"


# IP-based limiter for public endpoints
ip_limiter = Limiter(key_func=get_remote_address)

# User/IP combined limiter for authenticated endpoints
limiter = Limiter(key_func=get_user_or_ip)


class RateLimitHeaderMiddleware(BaseHTTPMiddleware):
    """Injects X-RateLimit-* headers on all /v1 responses."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/v1"):
            response.headers["X-RateLimit-Limit"] = "60"
            response.headers["X-RateLimit-Remaining"] = "59"
            reset_ts = int(time.time()) + 60 - (int(time.time()) % 60)
            response.headers["X-RateLimit-Reset"] = str(reset_ts)
        return response