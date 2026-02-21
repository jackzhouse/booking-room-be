"""
Test script for User Management API endpoints
Run this after starting the server to test the endpoints
"""
import asyncio
import httpx
import json
from typing import Optional

# Base URL - change if your server runs on different port
BASE_URL = "http://localhost:8000"


async def test_get_all_users(token: str, role: Optional[str] = None):
    """Test GET /api/v1/admin/users endpoint"""
    url = f"{BASE_URL}/api/v1/admin/users"
    params = {}
    if role:
        params["role"] = role
    
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        
        print(f"\n{'='*60}")
        print(f"GET {url} with role={role or 'all'}")
        print(f"Status: {response.status_code}")
        print(f"Response:")
        print(json.dumps(response.json(), indent=2))
        
        return response.status_code == 200


async def test_toggle_admin_role(token: str, user_id: str, is_admin: bool):
    """Test PATCH /api/v1/admin/users/{userId}/admin endpoint"""
    url = f"{BASE_URL}/api/v1/admin/users/{user_id}/admin"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {"is_admin": is_admin}
    
    async with httpx.AsyncClient() as client:
        response = await client.patch(url, headers=headers, json=data)
        
        print(f"\n{'='*60}")
        print(f"PATCH {url}")
        print(f"Request: {json.dumps(data)}")
        print(f"Status: {response.status_code}")
        print(f"Response:")
        print(json.dumps(response.json(), indent=2))
        
        return response.status_code == 200


async def test_toggle_active_status(token: str, user_id: str, is_active: bool):
    """Test PATCH /api/v1/admin/users/{userId}/status endpoint"""
    url = f"{BASE_URL}/api/v1/admin/users/{user_id}/status"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {"is_active": is_active}
    
    async with httpx.AsyncClient() as client:
        response = await client.patch(url, headers=headers, json=data)
        
        print(f"\n{'='*60}")
        print(f"PATCH {url}")
        print(f"Request: {json.dumps(data)}")
        print(f"Status: {response.status_code}")
        print(f"Response:")
        print(json.dumps(response.json(), indent=2))
        
        return response.status_code == 200


async def main():
    """Main test function"""
    print("User Management API Test Suite")
    print("="*60)
    
    # Note: You need to provide a valid admin JWT token
    # Get it by logging in through the frontend or auth endpoint
    token = input("\nEnter your admin JWT token (or press Enter to skip tests): ").strip()
    
    if not token:
        print("\nNo token provided. Skipping tests.")
        print("\nTo get a token:")
        print("1. Login through the frontend")
        print("2. Or use the /api/v1/auth endpoint")
        return
    
    try:
        # Test 1: Get all users
        await test_get_all_users(token, role="all")
        
        # Test 2: Get only admin users
        await test_get_all_users(token, role="admin")
        
        # Get a user ID for testing update operations
        response = await httpx.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        users = response.json().get("users", [])
        
        if users:
            user_id = users[0]["id"]
            print(f"\nUsing user ID for testing: {user_id}")
            
            # Test 3: Toggle admin role to True
            await test_toggle_admin_role(token, user_id, is_admin=True)
            
            # Test 4: Toggle admin role back to False
            await test_toggle_admin_role(token, user_id, is_admin=False)
            
            # Test 5: Toggle active status to False
            await test_toggle_active_status(token, user_id, is_active=False)
            
            # Test 6: Toggle active status back to True
            await test_toggle_active_status(token, user_id, is_active=True)
        else:
            print("\nNo users found in database. Create some users first.")
        
        print("\n" + "="*60)
        print("All tests completed!")
        
    except Exception as e:
        print(f"\nError during testing: {e}")


if __name__ == "__main__":
    asyncio.run(main())