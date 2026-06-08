import asyncio
import hashlib
import hmac
import json
import secrets
import uuid
from typing import List, Tuple

import httpx
import structlog
from sqlalchemy.orm import Session

from app.models.webhook import Webhook, WebhookDelivery

logger = structlog.get_logger()


def create_webhook(
    db: Session,
    user_id: uuid.UUID,
    url: str,
    event_types: List[str],
) -> Tuple[Webhook, str]:
    """Create a webhook and return (webhook, plaintext_secret). Secret returned once."""
    secret = secrets.token_hex(32)
    wh = Webhook(
        user_id=user_id,
        url=url,
        event_types=event_types,
        secret=secret,
    )
    db.add(wh)
    db.commit()
    db.refresh(wh)
    return wh, secret


def list_webhooks(
    db: Session,
    user_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[Webhook], int]:
    q = db.query(Webhook).filter(Webhook.user_id == user_id)
    total = q.count()
    items = q.offset(offset).limit(limit).all()
    return items, total


def delete_webhook(db: Session, webhook_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    wh = db.query(Webhook).filter(
        Webhook.id == webhook_id,
        Webhook.user_id == user_id,
    ).first()
    if not wh:
        return False
    db.delete(wh)
    db.commit()
    return True


def get_delivery_history(
    db: Session,
    webhook_id: uuid.UUID,
    user_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[WebhookDelivery], int]:
    # Verify ownership
    wh = db.query(Webhook).filter(
        Webhook.id == webhook_id,
        Webhook.user_id == user_id,
    ).first()
    if not wh:
        return [], 0
    q = (
        db.query(WebhookDelivery)
        .filter(WebhookDelivery.webhook_id == webhook_id)
        .order_by(WebhookDelivery.attempted_at.desc())
    )
    total = q.count()
    items = q.offset(offset).limit(limit).all()
    return items, total


def trigger_webhook(
    db: Session,
    user_id: uuid.UUID,
    event_type: str,
    payload: dict,
) -> None:
    """Fire-and-forget: dispatches asyncio tasks for all active webhooks matching this user+event.

    Never raises — all exceptions are swallowed.
    """
    try:
        webhooks = db.query(Webhook).filter(
            Webhook.user_id == user_id,
            Webhook.active == True,  # noqa: E712
            Webhook.event_types.contains([event_type]),
        ).all()

        for wh in webhooks:
            try:
                asyncio.create_task(_deliver(db, wh, event_type, payload))
            except Exception as e:
                logger.warning(
                    "webhook_task_creation_failed",
                    webhook_id=str(wh.id),
                    error=str(e),
                )
    except Exception as e:
        logger.warning("trigger_webhook_failed", event_type=event_type, error=str(e))


async def _deliver(
    db: Session,
    wh: Webhook,
    event_type: str,
    payload: dict,
) -> None:
    """Make HTTP POST and record the delivery result. Never raises."""
    body = json.dumps(payload, default=str)
    sig = hmac.new(
        wh.secret.encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()

    delivery = WebhookDelivery(
        webhook_id=wh.id,
        event_type=event_type,
        payload=payload,
        status="failed",
    )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                wh.url,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Aegis-Signature": f"sha256={sig}",
                },
            )
            delivery.status = "success" if resp.status_code < 400 else "failed"
            delivery.response_code = resp.status_code
    except Exception as e:
        delivery.error_message = str(e)
        logger.warning(
            "webhook_delivery_failed",
            webhook_id=str(wh.id),
            error=str(e),
        )

    try:
        db.add(delivery)
        db.commit()
    except Exception:
        pass  # Never raise from delivery
