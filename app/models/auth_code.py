"""
Authorization Code Model.
Stores temporary codes for Telegram bot authorization.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from beanie import Document, Indexed, PydanticObjectId

from app.core.config import settings


class AuthCode(Document):
    """Authorization code for Telegram bot authentication."""
    
    code: str = Indexed(unique=True, max_length=6)
    """6-digit authorization code."""
    
    telegram_user_id: Optional[int] = None
    """Telegram user ID this code is authorized for (set during generation)."""
    
    telegram_user_data: Optional[Dict[str, Any]] = None
    """Telegram user data associated with this code (after verification)."""

    purpose: str = "login"
    """Code purpose: login or telegram_link."""

    target_user_id: Optional[PydanticObjectId] = None
    """Local user that owns a telegram_link code."""

    completion_error: Optional[str] = None
    """Terminal link error, such as TELEGRAM_ALREADY_LINKED."""
    
    created_at: datetime
    """Timestamp when code was created."""
    
    expires_at: datetime
    """Timestamp when code expires."""
    
    used: bool = False
    """Whether code has been used."""
    
    used_at: Optional[datetime] = None
    """Timestamp when code was used."""
    
    class Settings:
        name = "auth_codes"
        indexes = [
            # Index on code for fast lookup
            "code",
            # TTL index to auto-expire codes after expiration
            [("expires_at", 1)]
        ]
        
        # Time-to-live index for automatic document expiration
        use_state_management = False
