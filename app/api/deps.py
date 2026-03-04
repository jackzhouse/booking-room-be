from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from bson import ObjectId

from app.core.security import decode_access_token, verify_telegram_hash, verify_telegram_init_data, verify_external_token
from app.models.user import User

security = HTTPBearer()


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
        if user_id is None:
            raise credentials_exception
        
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
        # Get external user ID from token
        external_user_id: str = external_payload.get("userId")
        if external_user_id is None:
            raise credentials_exception
        
        # Get user from database by external_user_id
        user = await User.find_one(
            User.external_user_id == external_user_id
        )
        
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