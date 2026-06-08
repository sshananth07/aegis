import jwt
import httpx
import hashlib
import structlog
from typing import Optional
from fastapi import Depends, Header, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.base import get_db

logger = structlog.get_logger()
security = HTTPBearer()

_jwks_cache: dict = {}

async def get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
        )
        response.raise_for_status()
        _jwks_cache = response.json()
        return _jwks_cache

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> dict:
    token = credentials.credentials

    try:
        header = jwt.get_unverified_header(token)
        algorithm = header.get("alg", "ES256")

        jwks = await get_jwks()
        keys = {key["kid"]: key for key in jwks["keys"]}

        if header.get("kid") not in keys:
            # Reset cache and retry once
            _jwks_cache.clear()
            jwks = await get_jwks()
            keys = {key["kid"]: key for key in jwks["keys"]}

        if header.get("kid") not in keys:
            raise HTTPException(status_code=401, detail="Invalid token key")

        key_data = keys[header["kid"]]

        if algorithm == "ES256":
            from jwt.algorithms import ECAlgorithm
            public_key = ECAlgorithm.from_jwk(key_data)
        elif algorithm == "RS256":
            from jwt.algorithms import RSAAlgorithm
            public_key = RSAAlgorithm.from_jwk(key_data)
        else:
            raise HTTPException(
                status_code=401,
                detail=f"Unsupported algorithm: {algorithm}"
            )

        payload = jwt.decode(
            token,
            public_key,
            algorithms=[algorithm],
            options={"verify_aud": False}
        )

        logger.info("auth_success", user_id=payload.get("sub"))
        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("auth_failed", error=str(e))
        raise HTTPException(status_code=401, detail="Authentication failed")

def get_user_id(user: dict = Depends(get_current_user)) -> str:
    return user["sub"]


async def get_api_key_user(
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> tuple:
    """Returns (user_id_str, scopes) or raises HTTP 401."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="X-API-Key header required")
    from app.services.api_key_service import validate_api_key
    result = validate_api_key(db, x_api_key)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid or expired API key")
    user_id, scopes = result
    return str(user_id), scopes


def require_scope(scope: str):
    """Dependency factory. Usage: user_id = Depends(require_scope('evaluations:write'))"""
    async def check(api_key_data: tuple = Depends(get_api_key_user)):
        user_id, scopes = api_key_data
        if scope not in scopes:
            raise HTTPException(status_code=403, detail=f"Scope '{scope}' required")
        return user_id
    return check