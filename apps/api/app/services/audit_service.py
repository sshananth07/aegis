import uuid
import structlog
from typing import Optional
from sqlalchemy.orm import Session
from app.models.audit import AuditEvent
from app.models.api_usage import APIUsage

logger = structlog.get_logger()


def log_event(
    db: Session,
    user_id: uuid.UUID,
    action: str,
    api_key_id: Optional[uuid.UUID] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[uuid.UUID] = None,
    metadata: Optional[dict] = None,
) -> None:
    """Fire-and-forget audit write. Swallows all exceptions."""
    try:
        event = AuditEvent(
            user_id=user_id,
            api_key_id=api_key_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata_=metadata or {},
        )
        db.add(event)
        db.commit()
    except Exception as e:
        logger.warning("audit_log_failed", error=str(e))


def log_usage(
    db: Session,
    api_key_id: uuid.UUID,
    endpoint: str,
    method: str,
    status_code: int,
    latency_ms: int,
) -> None:
    """Fire-and-forget usage write."""
    try:
        usage = APIUsage(
            api_key_id=api_key_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            latency_ms=latency_ms,
        )
        db.add(usage)
        db.commit()
    except Exception as e:
        logger.warning("usage_log_failed", error=str(e))
