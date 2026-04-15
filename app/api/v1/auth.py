from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Response
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from bson import ObjectId
from urllib.parse import urlencode
from pydantic import BaseModel
from jose import jwt, JWTError
import requests

from app.core.security import create_access_token, verify_telegram_hash, verify_telegram_init_data
from app.core.authz import user_has_admin_role, normalize_role, normalize_roles
from app.core.config import settings
from app.core.enums import RoleEnum, UserTypeEnum
from app.models.user import User
from app.schemas.auth import (
    TelegramLoginRequest,
    TelegramMiniAppRequest,
    TokenResponse,
    UserResponse,
    AuthCodeGenerateRequest,
    AuthCodeData,
    AuthCodeResponse,
    AuthCodeVerifyResponse,
    AuthCodeVerifyData,
    AuthCodeUserData,
    ExternalTokenVerifyRequest,
    ExternalTokenVerifyResponse,
    ExternalRegisterRequest,
    ExternalRegisterResponse,
    TokenLoginRequest,
    TokenData,
    TokenResponseLogin,
    TeacherCreateRequest,
    AdminCreateRequest,
    UserUpdateRequest,
    PasswordChangeRequest
)
from app.api.deps import get_current_user, get_current_admin_user, get_user_by_telegram_id
from app.services.auth_code_service import auth_code_service
from app.services.user_service import UserRepository


class TelegramUserAuth(BaseModel):
    """Telegram user data for code verification"""
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None

router = APIRouter(prefix="/auth", tags=["authentication"])

oauth2_scheme_external = OAuth2PasswordBearer(tokenUrl=f"{settings.PREFIX_NAME}/auth/external/login")


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
        
        # Set super admin role for designated Telegram admin account.
        if telegram_id == settings.ADMIN_TELEGRAM_ID:
            user.role = RoleEnum.SUPER_ADMIN
        elif user.role is None:
            user.role = RoleEnum.STUDENT
        
        await user.save()
    else:
        # Create new user
        role = RoleEnum.SUPER_ADMIN if telegram_id == settings.ADMIN_TELEGRAM_ID else RoleEnum.STUDENT
        user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            username=telegram_user_data.get("username"),
            avatar_url=telegram_user_data.get("photo_url"),
            role=role,
            user_type=UserTypeEnum.TELEGRAM,
            is_active=True,
            last_login_at=datetime.now(settings.timezone)
        )
        await user.insert()
    
    return user


def resolve_external_role(role: Optional[str], roles: Optional[list[str]]) -> Optional[RoleEnum]:
    """Resolve external role payload into system role."""
    normalized_roles = normalize_roles(roles)
    if RoleEnum.SUPER_ADMIN in normalized_roles:
        return RoleEnum.SUPER_ADMIN
    if RoleEnum.ADMIN in normalized_roles:
        return RoleEnum.ADMIN

    normalized_role = normalize_role(role)
    if normalized_role:
        return normalized_role

    return None


async def get_current_user_external(token: str = Depends(oauth2_scheme_external)):
    """
    Get current external user from JWT token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("userId") is None:
            raise credentials_exception
        role_value = payload.get("role")
        if role_value is None and payload.get("roles"):
            role_value = payload.get("roles")[0]
        token_data = TokenData(
            user_id=payload.get("userId"),
            company_id=payload.get("companyId"),
            role=role_value
        )
        return token_data
    except JWTError:
        raise credentials_exception


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
        login_source="telegram",
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
        login_source="telegram_mini_app",
        user=UserResponse(**user.dict(by_alias=True))
    )


@router.post("/generate-code", response_model=AuthCodeResponse)
async def generate_auth_code(request: AuthCodeGenerateRequest):
    """
    Generate a new authentication code.
    
    If telegram_user_id is provided (Mini App), the code can only be used by that specific user.
    If telegram_user_id is None or not provided (Web), any user can use the code (first-come-first-served).
    
    Codes expire after 3 minutes.
    """
    code, expires_at = await auth_code_service.generate_code(request.telegram_user_id)
    
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
        
        # MongoDB stores UTC as naive datetime - convert properly
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc).astimezone(settings.timezone)
        
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
                role=user.role,
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
    success, error_msg = await auth_code_service.mark_code_used(code, telegram_user_data)
    
    if not success:
        # Handle different error cases
        if error_msg == "USER_MISMATCH":
            return AuthCodeVerifyResponse(
                success=False,
                data=AuthCodeVerifyData(status="invalid"),
                error={"code": "USER_MISMATCH", "message": "This code is not valid for your Telegram account"}
            )
        else:
            return AuthCodeVerifyResponse(
                success=False,
                data=AuthCodeVerifyData(status="expired"),
                error={"code": "CODE_ERROR", "message": error_msg or "Code processing error"}
            )
    
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
                role=user.role,
                is_active=user.is_active
            ),
        token=access_token
        )
    )


# External App Integration Endpoints

@router.post("/external/verify-token", response_model=ExternalTokenVerifyResponse)
async def verify_external_token_endpoint(request: ExternalTokenVerifyRequest):
    """
    Check external user registration status by accountId.
    """
    if not ObjectId.is_valid(request.account_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid accountId format. Expected Mongo ObjectId string."
        )
    
    # Check by account_id first, then fallback to legacy external_user_id.
    user = await User.find_one(User.account_id == request.account_id)
    if not user:
        user = await User.find_one(User.external_user_id == request.account_id)

    if user:
        # User already registered
        # Update last login
        user.last_login_at = datetime.now(settings.timezone)
        await user.save()
        
        return ExternalTokenVerifyResponse(
            success=True,
            registered=True,
            user=UserResponse(**user.dict(by_alias=True))
        )
    else:
        # User not registered, return info for registration
        return ExternalTokenVerifyResponse(
            success=True,
            registered=False,
            user_id=request.account_id
        )


@router.post("/external/register", response_model=ExternalRegisterResponse)
async def register_external_user_endpoint(request: ExternalRegisterRequest):
    """
    Register a new user from external user data.
    """
    if not ObjectId.is_valid(request.account_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid accountId format. Expected Mongo ObjectId string."
        )
    
    resolved_role = resolve_external_role(request.role, request.roles)

    # Check if user already exists by account_id or legacy external_user_id
    existing_user = await User.find_one(User.account_id == request.account_id)
    if not existing_user:
        existing_user = await User.find_one(User.external_user_id == request.account_id)

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already registered"
        )
    
    # Create new user
    user = User(
        telegram_id=None,  # null for external users
        account_id=request.account_id,
        full_name=request.full_name,
        division=request.division,
        email=request.email,
        telegram_username=request.telegram_username,
        username=request.username,
        external_user_id=request.user_id,
        external_company_id=request.company_id,
        external_producer=request.producer,
        role=resolved_role or RoleEnum.STUDENT,
        user_type=UserTypeEnum.EXTERNAL,
        is_active=True,
        company_id=request.company_id,
        created_at=datetime.now(settings.timezone),
        last_login_at=datetime.now(settings.timezone)
    )
    
    await user.insert()
    
    return ExternalRegisterResponse(
        success=True,
        message="User registered successfully",
        user=UserResponse(**user.dict(by_alias=True))
    )


# ===== Username/Password Authentication =====

@router.post("/login", response_model=TokenResponseLogin)
async def login_with_external_user_data(request: TokenLoginRequest):
    """
    Authenticate or auto-register external user using user data payload.
    """
    if not ObjectId.is_valid(request.account_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid accountId format. Expected Mongo ObjectId string."
        )

    user = await User.find_one(User.account_id == request.account_id)
    if not user:
        # Backward compatibility for old records that stored accountId in external_user_id.
        user = await User.find_one(User.external_user_id == request.account_id)

    resolved_role = resolve_external_role(request.role, request.roles)
    now = datetime.now(settings.timezone)

    if not user:
        fallback_name = request.full_name or request.username or f"External User {request.account_id[-6:]}"
        user = User(
            telegram_id=None,
            account_id=request.account_id,
            external_user_id=request.user_id,
            full_name=fallback_name,
            username=request.username,
            email=request.email,
            division=request.division,
            telegram_username=request.telegram_username,
            external_company_id=request.company_id,
            external_producer=request.producer,
            role=resolved_role or RoleEnum.STUDENT,
            user_type=UserTypeEnum.EXTERNAL,
            is_active=True,
            company_id=request.company_id,
            created_at=now,
            last_login_at=now
        )
        await user.insert()
    else:
        user.account_id = request.account_id
        if request.user_id:
            user.external_user_id = request.user_id
        if request.full_name:
            user.full_name = request.full_name
        if request.username:
            user.username = request.username
        if request.email:
            user.email = request.email
        if request.division:
            user.division = request.division
        if request.telegram_username:
            user.telegram_username = request.telegram_username
        if request.company_id:
            user.external_company_id = request.company_id
            user.company_id = request.company_id
        if request.producer:
            user.external_producer = request.producer
        user.user_type = UserTypeEnum.EXTERNAL
        if resolved_role:
            user.role = resolved_role
        user.last_login_at = now
        await user.save()

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Create access token
    token_data = {
        "sub": str(user.id),
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role.value if user.role else None,
        "roles": [user.role.value] if user.role else [],
        "company_id": user.company_id,
        "external_user_id": user.external_user_id,
        "account_id": user.account_id,
        "producer": user.external_producer,
        "login_source": "external_user_data"
    }
    access_token = create_access_token(data=token_data)
    
    # Calculate token expiration
    expires_delta = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    expires_in = int(expires_delta.total_seconds())
    
    return TokenResponseLogin(
        access_token=access_token,
        login_source="external_user_data",
        expires_in=expires_in,
        user=UserResponse(**user.dict(by_alias=True))
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Get current user information from JWT token.
    """
    return UserResponse(**current_user.dict(by_alias=True))


@router.put("/me/profile", response_model=UserResponse)
async def update_current_user_profile(
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update current user profile.
    """
    updated_user = await UserRepository.update_profile(
        user_id=str(current_user.id),
        request=request,
        updated_by=str(current_user.id)
    )
    return UserResponse(**updated_user.dict(by_alias=True))