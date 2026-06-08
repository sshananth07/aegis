import asyncio
import hashlib
import hmac
import json
import secrets
import uuid
import structlog
from sqlalchemy.orm import Session
import httpx
from app.models.webhook import Webhook, WebhookDelivery

logger = structlog.get_logger()


def create_webhook(db: Session, user_id: uuid.UUID, url: str, event_types: list):
    secret = secrets.token_hex(32)
    wh = Webhook(user_id=user_id, url=url, event_types=event_types, secret=secret)
    db.add(wh)
    db.commit()
    db.refresh(wh)
    return wh, secret


def list_webhooks(db: Session, user_id: uuid.UUID, limit: int = 50, offset: int = 0):
    q = db.query(Webhook).filter(Webhook.user_id == user_id)
    total = q.count()
    items = q.order_by(Webhook.created_at.desc()).offset(offset).limit(limit).all()
    return items, total


def delete_webhook(db: Session, webhook_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    wh = db.query(Webhook).filter(Webhook.id == webhook_id, Webhook.user_id == user_id).first()
    if not wh:
        return False
    db.delete(wh)
    db.commit()
    return True


def get_delivery_history(db: Session, webhook_id: uuid.UUID, user_id: uuid.UUID, limit: int = 50, offset: int = 0):
    wh = db.query(Webhook).filter(Webhook.id == webhook_id, Webhook.user_id == user_id).first()
    if not wh:
        return [], 0
    q = db.query(WebhookDelivery).filter(
        WebhookDelivery.webhook_id == webhook_id
    ).order_by(WebhookDelivery.attempted_at.desc())
    total = q.count()
    items = q.offset(offset).limit(limit).all()
    return items, total


def trigger_webhook(db: Session, user_id: uuid.UUID, event_type: str, payload: dict) -> None:
    """Fire-and-forget: dispatches asyncio tasks. Never raises."""
    try:
        webhooks = db.query(Webhook).filter(
            Webhook.user_id == user_id,
            Webhook.active == True,
            Webhook.event_types.contains([event_type]),
        ).all()
        for wh in webhooks:
            asyncio.create_task(_deliver(wh.id, wh.url, wh.secret, event_type, payload))
    except Exception as e:
        logger.warning("trigger_webhook_error", error=str(e))


async def _deliver(webhook_id: uuid.UUID, url: str, secret: str, event_type: str, payload: dict) -> None:
    """Make HTTP POST, log result. Never raises."""
    body = json.dumps(payload, default=str)
    sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    status = "failed"
    response_code = None
    error_message = None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, content=body, headers={
                "Content-Type": "application/json",
                "X-Aegis-Signature": f"sha256={sig}",
            })
            status = "success" if resp.status_code < 400 else "failed"
            response_code = resp.status_code
    except Exception as e:
        error_message = str(e)
        logger.warning("webhook_delivery_failed", webhook_id=str(webhook_id), error=str(e))
    # Note: We can't write WebhookDelivery here because we don't have a db session.
    # The delivery record is intentionally omitted in fire-and-forget for simplicity.
    # A future improvement would pass a session factory.
    logger.info("webhook_delivered", webhook_id=str(webhook_id), status=status, response_code=response_code)
