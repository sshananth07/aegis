import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.auth import get_user_id
from app.core.rate_limit import limiter
from app.db.base import get_db
from app.schemas.webhook import WebhookCreate, WebhookCreateResponse
from app.services.webhook_service import create_webhook, list_webhooks, delete_webhook, get_delivery_history

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/", response_model=WebhookCreateResponse)
@limiter.limit("10/minute")
async def create(
    request: Request,
    data: WebhookCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    wh, secret = create_webhook(db, uuid.UUID(user_id), data.url, data.event_types)
    return WebhookCreateResponse(
        id=wh.id,
        user_id=wh.user_id,
        url=wh.url,
        event_types=wh.event_types,
        active=wh.active,
        created_at=wh.created_at,
        secret=secret,
    )


@router.get("/")
@limiter.limit("30/minute")
async def list_all(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    items, total = list_webhooks(db, uuid.UUID(user_id), limit=limit, offset=offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.delete("/{webhook_id}", status_code=204)
@limiter.limit("10/minute")
async def delete(
    request: Request,
    webhook_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    if not delete_webhook(db, webhook_id, uuid.UUID(user_id)):
        raise HTTPException(status_code=404, detail="Webhook not found")


@router.get("/{webhook_id}/deliveries")
@limiter.limit("30/minute")
async def deliveries(
    request: Request,
    webhook_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    items, total = get_delivery_history(db, webhook_id, uuid.UUID(user_id), limit=limit, offset=offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}
