from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from bson import ObjectId

from app.core.security import decode_access_token, verify_telegram_hash, verify_telegram_init_data, verify_external_token
from app.models.user import User
from app.services.katalis_service import ExternalAuthError, extract_external_user_id, katalis_service

security = HTTPBearer()


async def _find_external_user_by_candidates(*external_user_ids: Optional[str]) -> Optional[User]:
    seen = set()
    for external_user_id in external_user_ids:
        if not external_user_id or external_user_id in seen:
            continue
        seen.add(external_user_id)

        user = await User.find_one(User.external_user_id == external_user_id)
        if user is not None:
            return user

    return None


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
    
    # Try Katalis JWT first. Katalis tokens identify users with accountId/userId,
    # while local Booking tokens identify users with sub.
    external_payload = verify_external_token(token)
    if external_payload:
        user = await _find_external_user_by_candidates(
            external_payload.get("accountId"),
            external_payload.get("userId"),
        )

        if user is None:
            raise credentials_exception

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )

        return user

    # Try to decode as BE JWT token (for Telegram/local Booking users)
    payload = decode_access_token(token)
    if payload:
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception

        user = await User.get(user_id)
        if user is None:
            raise credentials_exception

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )

        return user

    # Fallback: validate opaque Katalis token against credential endpoint.
    try:
        external_employee = await katalis_service.get_current_employee(token)
    except ExternalAuthError:
        external_employee = None

    if external_employee:
        external_user_id = extract_external_user_id(external_employee)
        if external_user_id is None:
            raise credentials_exception

        user = await _find_external_user_by_candidates(external_user_id)

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
    if not current_user.is_admin:
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
