from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

def get_user_or_ip(request: Request) -> str:
    """Use user ID for authenticated requests, IP for unauthenticated."""
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        token = auth.split(" ")[1]
        # Use first 16 chars of token as key (don't expose full token)
        return f"user:{token[:16]}"
    return f"ip:{get_remote_address(request)}"

# IP-based limiter for public endpoints
ip_limiter = Limiter(key_func=get_remote_address)

# User/IP combined limiter for authenticated endpoints
limiter = Limiter(key_func=get_user_or_ip)