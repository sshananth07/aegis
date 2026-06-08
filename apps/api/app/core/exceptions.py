from fastapi import Request
from fastapi.responses import JSONResponse


class AegisAPIException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


async def aegis_exception_handler(request: Request, exc: AegisAPIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


# Convenience factory functions

def invalid_api_key():
    return AegisAPIException("invalid_api_key", "Invalid or expired API key", 401)


def expired_api_key():
    return AegisAPIException("expired_api_key", "API key has expired", 401)


def scope_denied(scope: str):
    return AegisAPIException("scope_denied", f"Scope '{scope}' required", 403)


def resource_not_found(resource: str = "Resource"):
    return AegisAPIException("resource_not_found", f"{resource} not found", 404)


def rate_limit_exceeded():
    return AegisAPIException("rate_limit_exceeded", "Rate limit exceeded", 429)


def validation_error(msg: str):
    return AegisAPIException("validation_error", msg, 422)


def provider_unavailable():
    return AegisAPIException("provider_unavailable", "LLM provider is unavailable", 503)


def idempotency_conflict():
    return AegisAPIException("idempotency_conflict", "Idempotency key conflict", 409)
