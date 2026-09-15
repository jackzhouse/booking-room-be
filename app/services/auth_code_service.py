"""
Service for managing authentication codes.
Stores codes in MongoDB with expiration tracking.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import secrets
from bson import ObjectId

from app.core.config import settings
from app.models.auth_code import AuthCode
from app.models.user import User


class LinkCodeRateLimitError(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Try again in {retry_after} seconds")


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
    
    async def generate_code(
        self,
        telegram_user_id: Optional[int] = None,
        *,
        purpose: str = "login",
        target_user_id: Optional[ObjectId] = None,
    ) -> tuple[str, datetime]:
        """
        Generate a random 6-digit authentication code.
        
        Args:
            telegram_user_id: Telegram user ID to authorize the code for (optional)
                           If provided, code can only be used by this user
                           If None, code can be used by any user (first-come-first-served)
        
        Returns:
            Tuple of (code, expires_at in Jakarta timezone)
        """
        # Get current time in Jakarta timezone
        now = datetime.now(settings.timezone)
        
        # Generate unique 6-digit random code
        max_attempts = 10
        for _ in range(max_attempts):
            code = f"{secrets.randbelow(1_000_000):06d}"
            
            # Check if code already exists
            existing = await AuthCode.find_one(AuthCode.code == code)
            if not existing:
                break
        else:
            raise ValueError("Could not generate unique code after multiple attempts")
        
        # Calculate expiration time
        expires_at_jakarta = now + timedelta(minutes=self.code_expiry_minutes)
        
        # Store code in database using UTC for consistent storage
        # MongoDB will store as UTC, we'll convert to Jakarta when reading
        auth_code = AuthCode(
            code=code,
            telegram_user_id=telegram_user_id,  # Optional: Link code to specific user if provided
            purpose=purpose,
            target_user_id=target_user_id,
            created_at=now.astimezone(timezone.utc),
            expires_at=expires_at_jakarta.astimezone(timezone.utc),
            used=False
        )
        await auth_code.insert()
        
        if telegram_user_id:
            print(f"✅ AuthCodeService: Generated and saved code: {code} for user {telegram_user_id}")
        else:
            print(f"✅ AuthCodeService: Generated and saved code: {code} (no user restriction)")
        print(f"✅ Expires at (UTC): {expires_at_jakarta.astimezone(timezone.utc)}")
        print(f"✅ Expires at (Jakarta): {expires_at_jakarta}")
        
        return code, expires_at_jakarta

    async def generate_link_code(self, target_user_id: ObjectId) -> tuple[str, datetime]:
        now_utc = datetime.now(timezone.utc)
        pending_codes = await AuthCode.find({
            "purpose": "telegram_link",
            "target_user_id": target_user_id,
            "used": False,
        }).to_list()

        newest_pending = max(pending_codes, key=lambda item: item.created_at, default=None)
        if newest_pending:
            created_at = newest_pending.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            age_seconds = (now_utc - created_at).total_seconds()
            if age_seconds < 10:
                raise LinkCodeRateLimitError(max(1, int(10 - age_seconds)))

        for pending_code in pending_codes:
            pending_code.used = True
            pending_code.used_at = now_utc
            pending_code.completion_error = "CODE_REPLACED"
            await pending_code.save()

        return await self.generate_code(
            purpose="telegram_link",
            target_user_id=target_user_id,
        )
    
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
        
        print(f"🔍 AuthCodeService: Code details - used={auth_code.used}, has_user_data={auth_code.telegram_user_data is not None}, expires_at={auth_code.expires_at}")
        
        # Get current time in UTC (aware)
        now_utc = datetime.now(timezone.utc).replace(microsecond=0)
        
        # Convert expires_at to aware UTC (MongoDB stores as naive UTC)
        if auth_code.expires_at.tzinfo is None:
            expires_at_utc = auth_code.expires_at.replace(tzinfo=timezone.utc)
        else:
            expires_at_utc = auth_code.expires_at
        
        # Strip microseconds for consistent comparison
        expires_at_utc = expires_at_utc.replace(microsecond=0)
        
        # Convert to Jakarta timezone for display and response
        now_jakarta = now_utc.astimezone(settings.timezone)
        expires_at_jakarta = expires_at_utc.astimezone(settings.timezone)
        
        print(f"🔍 AuthCodeService: Current time (UTC): {now_utc}, Expires (UTC): {expires_at_utc}")
        print(f"🔍 AuthCodeService: Current time (Jakarta): {now_jakarta}, Expires (Jakarta): {expires_at_jakarta}")
        
        # Check if code is expired (compare aware UTC datetimes)
        if now_utc > expires_at_utc:
            print(f"🔍 AuthCodeService: Code expired (now={now_utc} > expires_at={expires_at_utc})")
            return None
        
        # Check if code is already used
        if auth_code.used:
            # If code has user data, it was used by bot - allow verification
            if auth_code.telegram_user_data:
                print(f"🔍 AuthCodeService: Code used but has user data - allowing verification")
                auth_code.expires_at = expires_at_jakarta
                return auth_code
            # If code is used but has no user data, reject it
            print(f"🔍 AuthCodeService: Code already used without user data")
            return None
        
        # Code is valid - update expires_at to Jakarta timezone for consistency
        auth_code.expires_at = expires_at_jakarta
        print(f"🔍 AuthCodeService: Code is valid!")
        return auth_code
    
    async def mark_code_used(self, code: str, user_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Mark a code as used and associate it with user data.
        Validates that the Telegram user ID matches the authorized user ID.
        
        Args:
            code: The authentication code
            user_data: User data to associate with code
            
        Returns:
            Tuple of (success, error_message)
        """
        # Find code
        auth_code = await AuthCode.find_one(AuthCode.code == code)
        
        if not auth_code:
            return False, "Code not found"

        if auth_code.purpose == "telegram_link":
            return False, "LINK_CODE_REQUIRES_LINK_COMPLETION"
        
        # Check if code is already used
        if auth_code.used:
            return False, "Code already used"
        
        # Validate telegram_user_id matches (only if telegram_user_id is set)
        # If telegram_user_id is None (web user), allow first-come-first-served
        authorized_user_id = auth_code.telegram_user_id
        requesting_user_id = user_data.get("id")
        
        # Only validate if code has a user ID restriction
        if authorized_user_id is not None and requesting_user_id != authorized_user_id:
            print(f"❌ AuthCodeService: User mismatch - Code authorized for {authorized_user_id}, requested by {requesting_user_id}")
            return False, "USER_MISMATCH"
        
        # Update code with user data - store used_at in UTC
        now_jakarta = datetime.now(settings.timezone)
        auth_code.telegram_user_data = user_data
        auth_code.used = True
        auth_code.used_at = now_jakarta.astimezone(timezone.utc)
        
        await auth_code.save()
        print(f"✅ AuthCodeService: Code {code} marked as used by user {requesting_user_id}")
        return True, ""

    async def complete_telegram_link(
        self,
        code: str,
        telegram_user_data: Dict[str, Any],
    ) -> tuple[bool, str, Optional[User]]:
        """Bind verified Telegram identity to link-code owner."""
        auth_code = await AuthCode.find_one(AuthCode.code == code)
        if not auth_code or auth_code.purpose != "telegram_link" or not auth_code.target_user_id:
            return False, "CODE_NOT_FOUND", None

        now_utc = datetime.now(timezone.utc)
        expires_at = auth_code.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if auth_code.used or now_utc > expires_at:
            return False, "CODE_EXPIRED", None

        target_user = await User.get(auth_code.target_user_id)
        if not target_user or target_user.is_deleted or not target_user.is_active:
            auth_code.used = True
            auth_code.used_at = now_utc
            auth_code.completion_error = "TARGET_USER_UNAVAILABLE"
            await auth_code.save()
            return False, auth_code.completion_error, None

        telegram_id = telegram_user_data.get("id")
        if not isinstance(telegram_id, int):
            return False, "INVALID_TELEGRAM_USER", None

        linked_user = await User.find_one(User.telegram_id == telegram_id)
        if linked_user and linked_user.id != target_user.id:
            auth_code.telegram_user_data = telegram_user_data
            auth_code.used = True
            auth_code.used_at = now_utc
            auth_code.completion_error = "TELEGRAM_ALREADY_LINKED"
            await auth_code.save()
            return False, auth_code.completion_error, None

        if target_user.telegram_id is not None and target_user.telegram_id != telegram_id:
            auth_code.telegram_user_data = telegram_user_data
            auth_code.used = True
            auth_code.used_at = now_utc
            auth_code.completion_error = "TARGET_ALREADY_LINKED"
            await auth_code.save()
            return False, auth_code.completion_error, None

        username = telegram_user_data.get("username")
        target_user.telegram_id = telegram_id
        target_user.telegram_username = f"@{username}" if username else None
        target_user.last_login_at = now_utc
        target_user.updated_at = now_utc
        await target_user.save()

        auth_code.telegram_user_id = telegram_id
        auth_code.telegram_user_data = telegram_user_data
        auth_code.used = True
        auth_code.used_at = now_utc
        auth_code.completion_error = None
        await auth_code.save()
        return True, "", target_user

    async def get_link_status(self, code: str, target_user_id: ObjectId) -> Dict[str, Any]:
        auth_code = await AuthCode.find_one(AuthCode.code == code)
        if (
            not auth_code
            or auth_code.purpose != "telegram_link"
            or auth_code.target_user_id != target_user_id
        ):
            return {"status": "expired", "error_code": "CODE_NOT_FOUND"}

        expires_at = auth_code.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        now_utc = datetime.now(timezone.utc)

        if auth_code.completion_error:
            return {
                "status": "conflict" if auth_code.completion_error in {
                    "TELEGRAM_ALREADY_LINKED",
                    "TARGET_ALREADY_LINKED",
                } else "expired",
                "error_code": auth_code.completion_error,
                "expires_at": expires_at,
                "expires_in": 0,
            }
        if auth_code.used and auth_code.telegram_user_id:
            username = (auth_code.telegram_user_data or {}).get("username")
            return {
                "status": "linked",
                "telegram_username": f"@{username}" if username else None,
                "expires_at": expires_at,
                "expires_in": 0,
            }
        if now_utc > expires_at:
            return {
                "status": "expired",
                "error_code": "CODE_EXPIRED",
                "expires_at": expires_at,
                "expires_in": 0,
            }
        return {
            "status": "pending",
            "expires_at": expires_at,
            "expires_in": int((expires_at - now_utc).total_seconds()),
        }
    
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
