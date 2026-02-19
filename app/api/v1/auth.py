from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from bson import ObjectId
from urllib.parse import urlencode
from pydantic import BaseModel

from app.core.security import create_access_token, verify_telegram_hash, verify_telegram_init_data
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import (
    TelegramLoginRequest,
    TelegramMiniAppRequest,
    TokenResponse,
    UserResponse,
    AuthCodeData,
    AuthCodeResponse,
    AuthCodeVerifyResponse,
    AuthCodeVerifyData,
    AuthCodeUserData
)
from app.api.deps import get_user_by_telegram_id
from app.services.auth_code_service import auth_code_service


class TelegramUserAuth(BaseModel):
    """Telegram user data for code verification"""
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None

router = APIRouter(prefix="/auth", tags=["authentication"])


def build_query_string_from_dict(data: Dict[str, Any]) -> str:
    """Build URL query string from dictionary."""
    return urlencode(data, doseq=True)


async def create_or_update_user(telegram_user_data: Dict[str, Any]) -> User:
    """
    Create or update user from Telegram data.
    
    Args:
        telegram_user_data: Dictionary containing Telegram user data
    
    Returns:
        User object
    """
    telegram_id = telegram_user_data["id"]
    
    # Check if user exists
    user = await get_user_by_telegram_id(telegram_id)
    
    # Build full name
    first_name = telegram_user_data.get("first_name", "")
    last_name = telegram_user_data.get("last_name", "")
    full_name = f"{first_name} {last_name}".strip()
    
    if user:
        # Update existing user
        user.full_name = full_name
        user.username = telegram_user_data.get("username")
        user.avatar_url = telegram_user_data.get("photo_url")
        user.last_login_at = datetime.now(settings.timezone)
        
        # Set admin if this is the first admin
        if telegram_id == settings.ADMIN_TELEGRAM_ID and not user.is_admin:
            user.is_admin = True
        
        await user.save()
    else:
        # Create new user
        user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            username=telegram_user_data.get("username"),
            avatar_url=telegram_user_data.get("photo_url"),
            is_admin=(telegram_id == settings.ADMIN_TELEGRAM_ID),
            is_active=True,
            last_login_at=datetime.now(settings.timezone)
        )
        await user.insert()
    
    return user


@router.post("/telegram", response_model=TokenResponse)
async def telegram_login(request: TelegramLoginRequest):
    """
    Authenticate user via Telegram Login Widget.
    
    Verifies the hash from Telegram and returns a JWT token.
    """
    # Build query string for verification
    data = {
        "id": request.id,
        "first_name": request.first_name,
        "auth_date": request.auth_date,
        "hash": request.hash
    }
    if request.last_name:
        data["last_name"] = request.last_name
    if request.username:
        data["username"] = request.username
    if request.photo_url:
        data["photo_url"] = request.photo_url
    
    query_string = build_query_string_from_dict(data)
    
    # Verify Telegram hash
    if not verify_telegram_hash(query_string):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram authentication"
        )
    
    # Create or update user
    user_data = {
        "id": request.id,
        "first_name": request.first_name,
        "last_name": request.last_name,
        "username": request.username,
        "photo_url": request.photo_url
    }
    user = await create_or_update_user(user_data)
    
    # Generate JWT token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(**user.dict(by_alias=True))
    )


@router.post("/tma", response_model=TokenResponse)
async def telegram_mini_app_login(request: TelegramMiniAppRequest):
    """
    Authenticate user via Telegram Mini App initData.
    
    Verifies the initData from Telegram Mini App and returns a JWT token.
    """
    # Verify Telegram initData
    user_data = verify_telegram_init_data(request.init_data)
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram Mini App authentication"
        )
    
    # Create or update user
    user = await create_or_update_user(user_data)
    
    # Generate JWT token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(**user.dict(by_alias=True))
    )


@router.post("/generate-code", response_model=AuthCodeResponse)
async def generate_auth_code():
    """
    Generate a new authentication code.
    
    The frontend can call this to get a 6-digit code that user
    can send to bot via /authorize command.
    
    Codes expire after 3 minutes.
    """
    code, expires_at = await auth_code_service.generate_code()
    
    # Calculate expires_in (seconds until expiration)
    now = datetime.now(settings.timezone)
    expires_in = int((expires_at - now).total_seconds())
    
    return AuthCodeResponse(
        success=True,
        data=AuthCodeData(
            code=code,
            expires_at=expires_at,
            expires_in=expires_in
        )
    )


@router.get("/verify-code", response_model=AuthCodeVerifyResponse)
async def verify_auth_code(code: str = Query(..., description="6-digit authentication code")):
    """
    Verify an authentication code status.
    
    Called by frontend to poll for code verification status.
    Returns pending/verified/expired status and user data if verified.
    """
    code_data = await auth_code_service.verify_code(code)
    
    if not code_data:
        # Code is invalid, expired, or already used
        return AuthCodeVerifyResponse(
            success=False,
            data=AuthCodeVerifyData(status="expired"),
            error={"code": "CODE_NOT_FOUND", "message": "Invalid authorization code"}
        )
    
    # Check if code has user data attached (from bot authorization)
    user_data = code_data.telegram_user_data
    
    if not user_data:
        # Code is valid but no user data yet - still pending
        now = datetime.now(settings.timezone)
        expires_at = code_data.expires_at
        expires_in = int((expires_at - now).total_seconds()) if expires_at > now else 0
        
        return AuthCodeVerifyResponse(
            success=True,
            data=AuthCodeVerifyData(
                status="pending",
                expires_at=expires_at,
                expires_in=expires_in
            )
        )
    
    # Code has user data - code was verified by bot
    # Create or update user and generate JWT token
    user = await create_or_update_user(user_data)
    access_token = create_access_token(data={"sub": str(user.id)})
    
    # Mark code as used (already marked by bot, but ensure it's saved)
    await auth_code_service.mark_code_used(code, user_data)
    
    # Extract first and last name from full_name
    full_name = user.full_name or ""
    name_parts = full_name.split(" ", 1)
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[1] if len(name_parts) > 1 else None
    
    return AuthCodeVerifyResponse(
        success=True,
        data=AuthCodeVerifyData(
            status="verified",
            user=AuthCodeUserData(
                id=str(user.id),
                telegram_id=user.telegram_id,
                username=user.username,
                first_name=first_name,
                last_name=last_name,
                photo_url=user.avatar_url,
                is_admin=user.is_admin,
                is_active=user.is_active
            ),
            token=access_token
        )
    )


@router.post("/verify-code-telegram", response_model=AuthCodeVerifyResponse)
async def verify_code_with_telegram(
    code: str = Query(..., description="6-digit authentication code"),
    telegram_user: TelegramUserAuth = Body(...)
):
    """
    Verify code and associate it with Telegram user data.
    
    This is called by bot when user sends /authorize {code} command.
    The bot provides Telegram user data which gets associated with code.
    
    On subsequent calls to /verify-code, user will be authenticated.
    """
    # Convert to dict
    telegram_user_data = telegram_user.dict()
    
    # Verify code exists and is valid
    code_data = await auth_code_service.verify_code(code)
    
    if not code_data:
        # Code is invalid, expired, or already used
        return AuthCodeVerifyResponse(
            success=False,
            data=AuthCodeVerifyData(status="expired"),
            error={"code": "CODE_NOT_FOUND", "message": "Invalid authorization code"}
        )
    
    # Associate Telegram user data with code
    await auth_code_service.mark_code_used(code, telegram_user_data)
    
    # Create or update user
    user = await create_or_update_user(telegram_user_data)
    
    # Generate JWT token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    # Extract first and last name from full_name
    full_name = user.full_name or ""
    name_parts = full_name.split(" ", 1)
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[1] if len(name_parts) > 1 else None
    
    return AuthCodeVerifyResponse(
        success=True,
        data=AuthCodeVerifyData(
            status="verified",
            user=AuthCodeUserData(
                id=str(user.id),
                telegram_id=user.telegram_id,
                username=user.username,
                first_name=first_name,
                last_name=last_name,
                photo_url=user.avatar_url,
                is_admin=user.is_admin,
                is_active=user.is_active
            ),
        token=access_token
        )
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_user_by_telegram_id)):
    """
    Get current user information.
    """
    # This endpoint should use JWT token, but for simplicity we're using telegram_id
    # In production, this should use get_current_user dependency
    return UserResponse(**current_user.dict(by_alias=True))
