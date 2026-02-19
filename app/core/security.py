from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from hashlib import sha256
import hmac
from urllib.parse import parse_qs

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify JWT access token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def verify_telegram_hash(query_string: str) -> bool:
    """
    Verify Telegram Login Widget or Mini App initData hash.
    
    Reference: https://core.telegram.org/widgets/login#checking-authorization
    Reference: https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app
    """
    try:
        # Parse query string
        params = parse_qs(query_string)
        
        # Extract hash
        auth_hash = params.get('hash', [None])[0]
        if not auth_hash:
            return False
        
        # Remove hash from params for checking
        params_without_hash = {k: v for k, v in params.items() if k != 'hash'}
        
        # Sort keys
        keys = sorted(params_without_hash.keys())
        
        # Build data check string
        data_check_string = []
        for key in keys:
            # Values are arrays, take the first element
            value = params_without_hash[key][0]
            data_check_string.append(f"{key}={value}")
        data_check_string = "\n".join(data_check_string)
        
        # Create secret key
        secret_key = sha256(settings.BOT_TOKEN.encode()).digest()
        
        # Compute hash
        computed_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            sha256
        ).hexdigest()
        
        # Compare hashes
        return computed_hash == auth_hash
        
    except Exception as e:
        print(f"Error verifying Telegram hash: {e}")
        return False


def verify_telegram_init_data(init_data: str) -> Dict[str, Any]:
    """
    Verify Telegram Mini App initData and return user data.
    
    Returns:
        Dictionary with user data if valid, None otherwise
    """
    if not verify_telegram_hash(init_data):
        return None
    
    try:
        params = parse_qs(init_data)
        user_data = params.get('user', [None])[0]
        
        if user_data:
            # Parse JSON string
            import json
            user = json.loads(user_data)
            return {
                'id': user.get('id'),
                'first_name': user.get('first_name'),
                'last_name': user.get('last_name', ''),
                'username': user.get('username'),
                'language_code': user.get('language_code'),
                'photo_url': user.get('photo_url')
            }
        
        return None
        
    except Exception as e:
        print(f"Error parsing Telegram init data: {e}")
        return None