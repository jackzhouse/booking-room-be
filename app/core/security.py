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
        return hmac.compare_digest(computed_hash, auth_hash)
        
    except Exception as e:
        print(f"Error verifying Telegram hash: {e}")
        return False


def verify_telegram_web_app_hash(init_data: str) -> bool:
    """Verify Telegram Mini App initData using the WebAppData secret."""
    try:
        params = parse_qs(init_data)
        auth_hash = params.get("hash", [None])[0]
        if not auth_hash:
            return False

        data_check_string = "\n".join(
            f"{key}={params[key][0]}"
            for key in sorted(params)
            if key != "hash"
        )
        secret_key = hmac.new(
            b"WebAppData",
            settings.BOT_TOKEN.encode(),
            sha256,
        ).digest()
        computed_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            sha256,
        ).hexdigest()
        return hmac.compare_digest(computed_hash, auth_hash)
    except (TypeError, ValueError, KeyError):
        return False


def validate_telegram_init_data(
    init_data: str,
    max_age_seconds: Optional[int] = None,
) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Validate signed Mini App data and return user plus stable error code."""
    if not verify_telegram_web_app_hash(init_data):
        return None, "INVALID_INIT_DATA"

    try:
        params = parse_qs(init_data)
        user_data = params.get('user', [None])[0]

        if max_age_seconds is not None:
            auth_date_value = params.get('auth_date', [None])[0]
            if not auth_date_value:
                return None, "INVALID_INIT_DATA"
            auth_date = datetime.fromtimestamp(int(auth_date_value), tz=dt_timezone.utc)
            age_seconds = (datetime.now(dt_timezone.utc) - auth_date).total_seconds()
            if age_seconds < -30 or age_seconds > max_age_seconds:
                return None, "INIT_DATA_EXPIRED"

        if not user_data:
            return None, "INVALID_INIT_DATA"

        import json
        user = json.loads(user_data)
        if not isinstance(user.get('id'), int):
            return None, "INVALID_INIT_DATA"
        return {
            'id': user.get('id'),
            'first_name': user.get('first_name'),
            'last_name': user.get('last_name', ''),
            'username': user.get('username'),
            'language_code': user.get('language_code'),
            'photo_url': user.get('photo_url')
        }, None
    except (TypeError, ValueError, KeyError):
        return None, "INVALID_INIT_DATA"


def verify_telegram_init_data(init_data: str, max_age_seconds: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Verify Telegram Mini App initData and return user data.
    
    Returns:
        Dictionary with user data if valid, None otherwise
    """
    user_data, _ = validate_telegram_init_data(init_data, max_age_seconds=max_age_seconds)
    return user_data


def verify_external_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify JWT token from external app (e.g., Katalis).
    
    Decodes and validates the token using the same SECRET_KEY used for BE JWT tokens.
    Returns payload if valid, None otherwise.
    
    Expected token structure:
    {
        "producer": "katalis",
        "userId": "695dcff40cdc7726a29f5006",
        "accountId": "695dcff40cdc7726a29f5005",
        "companyId": "0000000074739c67c2a1d6fe",
        "roles": ["ROLE_USER"],
        "permission": "",
        "exp": 1772156888,
        "iat": 1771984088
    }
    
    Returns:
        Dictionary with token payload if valid, None otherwise
    """
    try:
        # Decode token with SECRET_KEY (same as BE JWT tokens)
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
        
        # Validate producer
        if payload.get("producer") != settings.KATALIS_PRODUCER:
            print(f"Invalid producer: {payload.get('producer')}")
            return None
        
        # Validate required fields
        required_fields = ["userId", "companyId"]
        for field in required_fields:
            if field not in payload:
                print(f"Missing required field: {field}")
                return None
        
        return payload
        
    except JWTError as e:
        print(f"Error verifying external token: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error verifying external token: {e}")
        return None
