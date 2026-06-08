import hashlib
import secrets
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
import uuid

from sqlalchemy.orm import Session

from app.models.api_key import APIKey


def _generate_key() -> Tuple[str, str, str]:
    """Return (plaintext_key, prefix, hash)."""
    raw = secrets.token_urlsafe(32)
    plaintext = f"aegis_{raw}"
    prefix = plaintext[:8]
    key_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    return plaintext, prefix, key_hash


def create_api_key(
    db: Session,
    user_id: uuid.UUID,
    name: str,
    scopes: List[str],
    expires_in_days: Optional[int] = None,
) -> Tuple[APIKey, str]:
    """Create a new API key and return the ORM object plus the plaintext key."""
    plaintext, prefix, key_hash = _generate_key()

    expires_at = None
    if expires_in_days is not None:
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

    key_obj = APIKey(
        user_id=user_id,
        name=name,
        key_prefix=prefix,
        key_hash=key_hash,
        scopes=scopes,
        expires_at=expires_at,
    )
    db.add(key_obj)
    db.commit()
    db.refresh(key_obj)
    return key_obj, plaintext


def list_api_keys(
    db: Session,
    user_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[APIKey], int]:
    """Return a page of non-revoked API keys for the user plus the total count."""
    query = db.query(APIKey).filter(
        APIKey.user_id == user_id,
        APIKey.revoked == False,  # noqa: E712
    )
    total = query.count()
    items = query.order_by(APIKey.created_at.desc()).offset(offset).limit(limit).all()
    return items, total


def revoke_api_key(
    db: Session,
    key_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """Soft-delete an API key. Returns True if found and revoked, False otherwise."""
    key_obj = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == user_id,
        APIKey.revoked == False,  # noqa: E712
    ).first()

    if not key_obj:
        return False

    key_obj.revoked = True
    db.commit()
    return True
