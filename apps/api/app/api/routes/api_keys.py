from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
import uuid
from app.core.auth import get_user_id
from app.core.rate_limit import limiter
from app.db.base import get_db
from app.schemas.api_key import APIKeyCreate, APIKeyResponse, APIKeyCreateResponse
from app.services.api_key_service import create_api_key, revoke_api_key, list_api_keys


class APIKeyListResponse(BaseModel):
    items: List[APIKeyResponse]
    total: int
    limit: int
    offset: int

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.post("/", response_model=APIKeyCreateResponse)
@limiter.limit("10/minute")
async def create_key(
    request: Request,
    data: APIKeyCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    key_obj, plaintext = create_api_key(
        db, uuid.UUID(user_id), data.name, data.scopes, data.expires_in_days
    )
    return APIKeyCreateResponse(
        id=key_obj.id,
        user_id=key_obj.user_id,
        name=key_obj.name,
        key_prefix=key_obj.key_prefix,
        scopes=key_obj.scopes,
        last_used_at=key_obj.last_used_at,
        expires_at=key_obj.expires_at,
        revoked=key_obj.revoked,
        created_at=key_obj.created_at,
        key=plaintext,
    )


@router.get("/", response_model=APIKeyListResponse)
@limiter.limit("30/minute")
async def list_keys(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    items, total = list_api_keys(db, uuid.UUID(user_id), limit=limit, offset=offset)
    return APIKeyListResponse(items=items, total=total, limit=limit, offset=offset)


@router.delete("/{key_id}", status_code=204)
@limiter.limit("10/minute")
async def revoke_key(
    request: Request,
    key_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    success = revoke_api_key(db, key_id, uuid.UUID(user_id))
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
