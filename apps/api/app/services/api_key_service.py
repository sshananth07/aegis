import secrets
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.models.api_key import APIKey


def create_api_key(
    db: Session,
    user_id: uuid.UUID,
    name: str,
    scopes: list,
    expires_in_days: Optional[int] = None,
) -> tuple:
    """Returns (APIKey, plaintext_key). Plaintext is never stored."""
    plaintext = f"ak_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    key_prefix = plaintext[:16]
    api_key = APIKey(
        user_id=user_id,
        name=name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        scopes=scopes,
        expires_at=datetime.utcnow() + timedelta(days=expires_in_days) if expires_in_days else None,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key, plaintext


def validate_api_key(db: Session, plaintext: str) -> Optional[tuple]:
    """Returns (user_id UUID, scopes list) if valid, None otherwise. Updates last_used_at."""
    key_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    key = db.query(APIKey).filter(
        APIKey.key_hash == key_hash,
        APIKey.revoked.is_(False),
    ).first()
    if not key:
        return None
    if key.expires_at and key.expires_at < datetime.utcnow():
        return None
    key.last_used_at = datetime.utcnow()
    db.commit()
    return key.user_id, key.scopes


def revoke_api_key(db: Session, key_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    key = db.query(APIKey).filter(
        APIKey.id == key_id, APIKey.user_id == user_id
    ).first()
    if not key:
        return False
    key.revoked = True
    db.commit()
    return True


def get_key_by_id(db: Session, key_id: uuid.UUID, user_id: uuid.UUID) -> Optional[APIKey]:
    return db.query(APIKey).filter(
        APIKey.id == key_id, APIKey.user_id == user_id
    ).first()


def list_api_keys(db: Session, user_id: uuid.UUID, limit: int = 50, offset: int = 0) -> tuple:
    q = db.query(APIKey).filter(APIKey.user_id == user_id)
    total = q.count()
    items = q.order_by(APIKey.created_at.desc()).offset(offset).limit(limit).all()
    return items, total
