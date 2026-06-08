import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.core.auth import get_user_id
from app.core.rate_limit import limiter
from app.models.webhook import Webhook
from app.schemas.webhook import (
    WebhookCreate,
    WebhookCreateResponse,
    WebhookDeliveryResponse,
    WebhookResponse,
)
from app.services.webhook_service import (
    create_webhook,
    delete_webhook,
    get_delivery_history,
    list_webhooks,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/", response_model=WebhookCreateResponse)
@limiter.limit("20/minute")
def create(
    request: Request,
    data: WebhookCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    wh, secret = create_webhook(
        db=db,
        user_id=uuid.UUID(user_id),
        url=data.url,
        event_types=data.event_types,
    )
    return WebhookCreateResponse(
        id=wh.id,
        user_id=wh.user_id,
        url=wh.url,
        event_types=wh.event_types,
        active=wh.active,
        created_at=wh.created_at,
        secret=secret,
    )


@router.get("/", response_model=dict)
@limiter.limit("20/minute")
def list_all(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    items, total = list_webhooks(
        db=db,
        user_id=uuid.UUID(user_id),
        limit=limit,
        offset=offset,
    )
    return {
        "items": [WebhookResponse.model_validate(w) for w in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.delete("/{webhook_id}", status_code=204)
@limiter.limit("20/minute")
def delete(
    request: Request,
    webhook_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    deleted = delete_webhook(db=db, webhook_id=webhook_id, user_id=uuid.UUID(user_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Webhook not found")


@router.get("/{webhook_id}/deliveries", response_model=dict)
@limiter.limit("20/minute")
def list_deliveries(
    request: Request,
    webhook_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    wh = db.query(Webhook).filter(
        Webhook.id == webhook_id,
        Webhook.user_id == uuid.UUID(user_id),
    ).first()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")

    items, total = get_delivery_history(
        db=db,
        webhook_id=webhook_id,
        user_id=uuid.UUID(user_id),
        limit=limit,
        offset=offset,
    )
    return {
        "items": [WebhookDeliveryResponse.model_validate(d) for d in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
