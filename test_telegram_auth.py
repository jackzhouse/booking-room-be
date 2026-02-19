#!/usr/bin/env python3
"""
Test script to verify Telegram authentication hash generation
"""

from urllib.parse import urlencode, parse_qs
from hashlib import sha256
import hmac

# Load bot token from .env
BOT_TOKEN = "8421546523:AAERgz8eG3R0cqyzvtq3-U1K-hiP43jr67k"

def verify_telegram_hash_debug(query_string: str) -> tuple[bool, str]:
    """
    Debug version of verify_telegram_hash that returns result and details
    """
    try:
        # Parse query string
        params = parse_qs(query_string)
        
        # Extract hash
        auth_hash = params.get('hash', [None])[0]
        if not auth_hash:
            return False, "No hash found"
        
        print(f"Received hash: {auth_hash}")
        
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
        
        print(f"Data check string: {repr(data_check_string)}")
        
        # Create secret key
        secret_key = sha256(BOT_TOKEN.encode()).digest()
        print(f"Secret key (hex): {secret_key.hex()}")
        
        # Compute hash
        computed_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            sha256
        ).hexdigest()
        
        print(f"Computed hash: {computed_hash}")
        
        # Compare hashes (case-insensitive)
        return computed_hash.lower() == auth_hash.lower(), f"Hash match: {computed_hash.lower() == auth_hash.lower()}"
        
    except Exception as e:
        return False, f"Error: {e}"


# Test with sample data (simulating what would come from Telegram)
# This is just for testing - real data must come from Telegram
test_data = {
    "id": "123456789",
    "first_name": "Test",
    "last_name": "User",
    "username": "testuser",
    "auth_date": "1234567890",
    "hash": "test_hash"
}

query_string = urlencode(test_data, doseq=True)
print(f"Query string: {query_string}")
print()

result, details = verify_telegram_hash_debug(query_string)
print(f"\nResult: {result}")
print(f"Details: {details}")