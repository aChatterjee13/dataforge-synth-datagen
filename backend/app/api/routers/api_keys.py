from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import secrets

from app.api.models import APIKeyCreate, APIKeyResponse, APIKeyCreateResponse
from app.db.database import get_db, APIKey
from app.middleware.auth import hash_api_key
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/api-keys", response_model=APIKeyCreateResponse)
async def create_api_key(request: APIKeyCreate, db: Session = Depends(get_db)):
    """Create a new API key"""
    raw_key = f"df_{secrets.token_hex(24)}"
    key_hash = hash_api_key(raw_key)

    db_key = APIKey(
        key_hash=key_hash,
        name=request.name
    )
    db.add(db_key)
    db.commit()
    db.refresh(db_key)

    return APIKeyCreateResponse(
        id=db_key.id,
        name=db_key.name,
        key=raw_key,
        created_at=db_key.created_at
    )


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(db: Session = Depends(get_db)):
    """List all API keys (masked)"""
    keys = db.query(APIKey).order_by(APIKey.created_at.desc()).all()
    return [
        APIKeyResponse(
            id=k.id,
            name=k.name,
            key_preview=k.key_hash[:8] + "...",
            created_at=k.created_at,
            last_used=k.last_used
        )
        for k in keys
    ]


@router.delete("/api-keys/{key_id}")
async def delete_api_key(key_id: int, db: Session = Depends(get_db)):
    """Revoke an API key"""
    key = db.query(APIKey).filter(APIKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    db.delete(key)
    db.commit()
    return {"message": "API key revoked successfully"}
