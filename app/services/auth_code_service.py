"""
Service for managing authentication codes.
Stores codes in-memory with expiration tracking.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import random

from app.core.config import settings


class AuthCodeService:
    """Service for generating and verifying authentication codes."""
    
    def __init__(self):
        """Initialize the auth code service."""
        self.auth_codes: Dict[str, Dict[str, Any]] = {}
        self.code_expiry_minutes = 10  # Codes expire after 10 minutes
    
    def generate_code(self) -> tuple[str, datetime]:
        """
        Generate a random 6-digit authentication code.
        
        Returns:
            Tuple of (code, expires_at)
        """
        # Get current time in Jakarta timezone
        now = datetime.now(settings.timezone)
        
        # Generate 6-digit random code
        code = "".join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Calculate expiration time
        expires_at = now + timedelta(minutes=self.code_expiry_minutes)
        
        # Store the code with metadata
        self.auth_codes[code] = {
            "code": code,
            "created_at": now,
            "expires_at": expires_at,
            "used": False
        }
        
        # Clean up expired codes periodically
        self._cleanup_expired_codes()
        
        return code, expires_at
    
    def verify_code(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Verify an authentication code.
        
        Args:
            code: The authentication code to verify
            
        Returns:
            Dict with code data if valid, None otherwise
        """
        # Clean up expired codes first
        self._cleanup_expired_codes()
        
        # Check if code exists and is not used
        if code not in self.auth_codes:
            return None
        
        code_data = self.auth_codes[code]
        
        # Check if code is expired
        now = datetime.now(settings.timezone)
        if now > code_data["expires_at"]:
            del self.auth_codes[code]
            return None
        
        # Check if code is already used
        if code_data["used"]:
            return None
        
        # Code is valid
        return code_data
    
    def mark_code_used(self, code: str, user_data: Dict[str, Any]) -> bool:
        """
        Mark a code as used and associate it with user data.
        
        Args:
            code: The authentication code
            user_data: User data to associate with the code
            
        Returns:
            True if successfully marked, False otherwise
        """
        if code not in self.auth_codes:
            return False
        
        self.auth_codes[code]["used"] = True
        self.auth_codes[code]["user_data"] = user_data
        return True
    
    def _cleanup_expired_codes(self):
        """Remove expired codes from storage."""
        now = datetime.now(settings.timezone)
        expired_codes = [
            code for code, data in self.auth_codes.items()
            if now > data["expires_at"]
        ]
        for code in expired_codes:
            del self.auth_codes[code]
    
    def get_code_info(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a code without marking it as used.
        
        Args:
            code: The authentication code
            
        Returns:
            Dict with code data if exists, None otherwise
        """
        self._cleanup_expired_codes()
        return self.auth_codes.get(code)


# Global instance
auth_code_service = AuthCodeService()