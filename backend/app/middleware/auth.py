"""
API Key authentication middleware (Feature 8)
"""
import hashlib
from datetime import datetime, timezone
from typing import Optional

from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db, APIKey


def hash_api_key(key: str) -> str:
    """Hash an API key using SHA-256"""
    return hashlib.sha256(key.encode()).hexdigest()


async def verify_api_key(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[APIKey]:
    """
    Verify API key from X-API-Key header.
    Only enforced when API keys exist in the database.
    Returns the APIKey record if valid, None if no keys exist.
    """
    # Check if any API keys exist
    key_count = db.query(APIKey).count()
    if key_count == 0:
        # No keys configured — allow all requests
        return None

    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide X-API-Key header."
        )

    key_hash = hash_api_key(api_key)
    db_key = db.query(APIKey).filter(APIKey.key_hash == key_hash).first()

    if not db_key:
        raise HTTPException(status_code=403, detail="Invalid API key")

    # Update last_used timestamp
    db_key.last_used = datetime.now(timezone.utc)
    db.commit()

    return db_key
