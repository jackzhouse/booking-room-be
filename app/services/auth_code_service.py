"""
Service for managing authentication codes.
Stores codes in MongoDB with expiration tracking.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import random

from app.core.config import settings
from app.models.auth_code import AuthCode


def convert_utc_to_jakarta(dt: datetime) -> datetime:
    """
    Convert UTC datetime (naive or aware) to Jakarta timezone.
    
    Args:
        dt: Datetime object (can be naive UTC or aware)
    
    Returns:
        Datetime in Jakarta timezone
    """
    if dt.tzinfo is None:
        # Assume it's UTC and make it aware
        dt = dt.replace(tzinfo=timezone.utc)
    
    # Convert to Jakarta timezone
    return dt.astimezone(settings.timezone)


class AuthCodeService:
    """Service for generating and verifying authentication codes."""
    
    def __init__(self):
        """Initialize auth code service."""
        self.code_expiry_minutes = 3  # Codes expire after 3 minutes
    
    async def generate_code(self) -> tuple[str, datetime]:
        """
        Generate a random 6-digit authentication code.
        
        Returns:
            Tuple of (code, expires_at in Jakarta timezone)
        """
        # Get current time in Jakarta timezone
        now = datetime.now(settings.timezone)
        
        # Generate unique 6-digit random code
        max_attempts = 10
        for _ in range(max_attempts):
            code = "".join([str(random.randint(0, 9)) for _ in range(6)])
            
            # Check if code already exists
            existing = await AuthCode.find_one(AuthCode.code == code)
            # Only use if code doesn't exist or if it's already used
            if not existing or existing.used:
                break
        else:
            raise ValueError("Could not generate unique code after multiple attempts")
        
        # Calculate expiration time
        expires_at = now + timedelta(minutes=self.code_expiry_minutes)
        
        # Store code in database (MongoDB will convert to UTC)
        auth_code = AuthCode(
            code=code,
            created_at=now,
            expires_at=expires_at,
            used=False
        )
        await auth_code.insert()
        
        print(f"✅ AuthCodeService: Generated and saved code: {code} (expires at {expires_at})")
        
        return code, expires_at
    
    async def verify_code(self, code: str) -> Optional[AuthCode]:
        """
        Verify an authentication code.
        
        Args:
            code: The authentication code to verify
            
        Returns:
            AuthCode object if valid, None otherwise
        """
        print(f"🔍 AuthCodeService: Searching for code: {code}")
        
        # Find code document
        auth_code = await AuthCode.find_one(AuthCode.code == code)
        
        print(f"🔍 AuthCodeService: Found: {auth_code is not None}")
        
        if not auth_code:
            print(f"🔍 AuthCodeService: Code {code} not found in database")
            return None
        
        print(f"🔍 AuthCodeService: Code details - used={auth_code.used}, expires_at={auth_code.expires_at}")
        
        # Get current time in Jakarta timezone
        now = datetime.now(settings.timezone)
        
        # Convert expires_at to Jakarta timezone (MongoDB stores as UTC naive datetime)
        expires_at_jakarta = convert_utc_to_jakarta(auth_code.expires_at)
        
        print(f"🔍 AuthCodeService: Current time (Jakarta): {now}, Expires (Jakarta): {expires_at_jakarta}")
        
        # Check if code is expired
        if now > expires_at_jakarta:
            print(f"🔍 AuthCodeService: Code expired (now={now} > expires_at={expires_at_jakarta})")
            return None
        
        # Check if code is already used
        if auth_code.used:
            print(f"🔍 AuthCodeService: Code already used")
            return None
        
        # Code is valid - update expires_at to Jakarta timezone for consistency
        auth_code.expires_at = expires_at_jakarta
        print(f"🔍 AuthCodeService: Code is valid!")
        return auth_code
    
    async def mark_code_used(self, code: str, user_data: Dict[str, Any]) -> bool:
        """
        Mark a code as used and associate it with user data.
        
        Args:
            code: The authentication code
            user_data: User data to associate with code
            
        Returns:
            True if successfully marked, False otherwise
        """
        # Find and update code
        auth_code = await AuthCode.find_one(AuthCode.code == code)
        
        if not auth_code:
            return False
        
        # Update code with user data
        auth_code.telegram_user_data = user_data
        auth_code.used = True
        auth_code.used_at = datetime.now(settings.timezone)
        
        await auth_code.save()
        return True
    
    async def get_code_info(self, code: str) -> Optional[AuthCode]:
        """
        Get information about a code without marking it as used.
        
        Args:
            code: The authentication code
            
        Returns:
            AuthCode object if exists, None otherwise
        """
        return await AuthCode.find_one(AuthCode.code == code)


# Global instance
auth_code_service = AuthCodeService()