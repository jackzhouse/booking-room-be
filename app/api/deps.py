from typing import Optional, Any
from datetime import datetime
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from bson import ObjectId

from app.core.security import decode_access_token, verify_telegram_hash, verify_telegram_init_data, verify_external_token
from app.core.authz import user_has_admin_role, normalize_roles, normalize_role
from app.core.enums import RoleEnum, UserTypeEnum
from app.core.config import settings
from app.models.user import User

security = HTTPBearer()


def _resolve_external_role(payload: dict[str, Any]) -> RoleEnum:
    raw_roles = payload.get("roles") or []
    if not raw_roles and payload.get("role"):
        raw_roles = [payload.get("role")]

    token_roles = normalize_roles(raw_roles)
    if RoleEnum.SUPER_ADMIN in token_roles:
        return RoleEnum.SUPER_ADMIN
    if RoleEnum.ADMIN in token_roles:
        return RoleEnum.ADMIN
    if token_roles:
        for role in raw_roles:
            normalized = normalize_role(role)
            if normalized:
                return normalized
    return RoleEnum.STUDENT


async def _get_or_create_external_user(payload: dict[str, Any]) -> Optional[User]:
    account_id = payload.get("accountId") or payload.get("userId")
    external_user_id = payload.get("userId")
    if not account_id and not external_user_id:
        return None

    user = await User.find_one(User.account_id == account_id) if account_id else None
    if not user and external_user_id:
        user = await User.find_one(User.external_user_id == external_user_id)
    resolved_role = _resolve_external_role(payload)

    if user:
        user.account_id = account_id or user.account_id
        user.external_company_id = payload.get("companyId")
        user.external_producer = payload.get("producer")
        user.role = resolved_role
        user.last_login_at = datetime.now(settings.timezone)
        await user.save()
        return user

    try:
        forced_id = ObjectId(external_user_id or account_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid external account/user id format. Expected Mongo ObjectId string."
        )

    user = User(
        id=forced_id,
        telegram_id=None,
        account_id=account_id,
        external_user_id=external_user_id,
        external_company_id=payload.get("companyId"),
        external_producer=payload.get("producer"),
        username=payload.get("accountId"),
        full_name=payload.get("fullName") or f"External User {(external_user_id or account_id)[-6:]}",
        role=resolved_role,
        user_type=UserTypeEnum.EXTERNAL,
        is_active=True,
        company_id=payload.get("companyId"),
        last_login_at=datetime.now(settings.timezone)
    )
    await user.insert()
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Get the current authenticated user from either:
    1. BE JWT token (for Telegram users)
    2. External app JWT token (for external users like Katalis)
    
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    
    # Try to decode as BE JWT token (for Telegram users)
    payload = decode_access_token(token)
    if payload:
        # Get user ID from token
        user_id: str = payload.get("sub")
        if user_id is not None:
            # Get user from database
            user = await User.get(user_id)
            if user is None:
                raise credentials_exception
            
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is inactive"
                )
            
            return user
    
    # Try to decode as external app JWT token (for external users)
    external_payload = verify_external_token(token)
    if external_payload:
        user = await _get_or_create_external_user(external_payload)
        if user is None:
            raise credentials_exception
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        return user
    
    # Neither token type worked
    raise credentials_exception


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get the current active user.
    
    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get the current admin user.
    
    Raises:
        HTTPException: If user is not an admin
    """
    if not user_has_admin_role(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin access required."
        )
    return current_user


async def get_user_by_telegram_id(telegram_id: int) -> Optional[User]:
    """
    Get user by Telegram ID.
    Returns None if user not found.
    """
    return await User.find_one(User.telegram_id == telegram_id)


def verify_telegram_auth(query_string: str) -> bool:
    """
    Verify Telegram authentication data.
    
    Returns:
        True if valid, False otherwise
    """
    return verify_telegram_hash(query_string)
