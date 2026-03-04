"""
Test script for External App Integration (Katalis)
This script tests the new endpoints for external user authentication

Note: Katalis JWT tokens must be encoded with the same SECRET_KEY as Booking Room BE
"""
import asyncio
import sys
from datetime import datetime
import httpx

# Base URL for testing
BASE_URL = "http://localhost:8000"

# Test token - replace with actual Katalis JWT token for real testing
# This token must be encoded with the same SECRET_KEY as Booking Room BE
TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwcm9kdWNlciI6ImthdGFsaXMiLCJ1c2VySWQiOiI2OTVkY2ZmNDBjZGM3NzI2YTI5ZjUwMDYiLCJhY2NvdW50SWQiOiI2OTVkY2ZmNDBjZGM3NzI2YTI5ZjUwMDUiLCJjb21wYW55SWQiOiIwMDAwMDAwMDc0NzM5YzY3YzJhMWQ2ZmUiLCJyb2xlcyI6WyJST0xFX1VTRVIiXSwicGVybWlzc2lvbiI6IiIsImV4cCI6MTc3MjE1Njg4OCwiaWF0IjoxNzcxOTg0MDg4fQ.test_secret_key"


async def test_verify_token():
    """Test POST /api/v1/auth/external/verify-token endpoint"""
    print("\n=== Testing POST /api/v1/auth/external/verify-token ===")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/auth/external/verify-token",
            json={"token": TEST_TOKEN},
            timeout=10.0
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                if data.get("registered"):
                    print("✓ User already registered")
                    print(f"  User ID: {data['user']['id']}")
                else:
                    print("✓ User not registered, registration needed")
                    print(f"  External User ID: {data['user_id']}")
                    print(f"  Company ID: {data['company_id']}")
                    return data  # Return data for next test
            else:
                print("✗ Token verification failed")
        else:
            print(f"✗ Request failed: {response.text}")
    
    return None


async def test_register_user(token, full_name, division, email, telegram_username=None):
    """Test POST /api/v1/auth/external/register endpoint"""
    print("\n=== Testing POST /api/v1/auth/external/register ===")
    
    payload = {
        "token": token,
        "full_name": full_name,
        "division": division,
        "email": email
    }
    
    if telegram_username:
        payload["telegram_username"] = telegram_username
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/auth/external/register",
            json=payload,
            timeout=10.0
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print("✓ User registered successfully")
                print(f"  User ID: {data['user']['id']}")
                print(f"  Full Name: {data['user']['full_name']}")
                print(f"  Email: {data['user']['email']}")
                print(f"  External User ID: {data['user']['external_user_id']}")
                return data['user']
            else:
                print("✗ Registration failed")
        else:
            print(f"✗ Request failed: {response.text}")
    
    return None


async def test_get_me_with_external_token():
    """Test GET /api/v1/auth/me with external token"""
    print("\n=== Testing GET /api/v1/auth/me with external token ===")
    
    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/auth/me",
            headers=headers,
            timeout=10.0
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✓ External token authentication works")
            data = response.json()
            print(f"  User ID: {data['id']}")
            print(f"  Full Name: {data['full_name']}")
        else:
            print(f"✗ Authentication failed: {response.text}")


async def test_invalid_token():
    """Test with invalid token"""
    print("\n=== Testing with invalid token ===")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/auth/external/verify-token",
            json={"token": "invalid.token.here"},
            timeout=10.0
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 401:
            print("✓ Invalid token correctly rejected")
        else:
            print("✗ Should have returned 401 Unauthorized")


async def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("External App Integration Tests")
    print("=" * 60)
    
    # Test 1: Verify token
    verify_result = await test_verify_token()
    
    # Test 2: If user not registered, test registration
    if verify_result and not verify_result.get("registered"):
        print("\n--- Testing User Registration ---")
        await test_register_user(
            token=TEST_TOKEN,
            full_name="Test User External",
            division="Engineering",
            email="test.user@example.com",
            telegram_username="testuser_telegram"
        )
    
    # Test 3: Test authentication with external token
    await test_get_me_with_external_token()
    
    # Test 4: Test invalid token
    await test_invalid_token()
    
    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    # Check if server is running
    import socket
    
    def is_server_running(host, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    
    if not is_server_running("localhost", 8000):
        print("Error: Server is not running on localhost:8000")
        print("Please start the server first:")
        print("  uvicorn app.main:app --reload")
        sys.exit(1)
    
    # Run tests
    asyncio.run(run_all_tests())