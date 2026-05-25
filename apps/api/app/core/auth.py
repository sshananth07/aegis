import jwt
import httpx
import structlog
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

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