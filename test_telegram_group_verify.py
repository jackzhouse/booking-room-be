"""
Test script for Telegram Group Verification Feature

This script tests the new verify endpoint that fetches Telegram group information
automatically from Telegram API using only the group ID.

Prerequisites:
1. Bot token must be set in .env file
2. You need a valid admin token from the API
3. The bot must be added to the test group
4. Replace GROUP_ID with a valid Telegram group ID
"""

import asyncio
import httpx
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")  # Set this in .env or replace here
TEST_GROUP_ID = -1001234567890  # Replace with a real group ID for testing


async def test_verify_endpoint():
    """Test the verify endpoint with a real Telegram group"""
    
    if not ADMIN_TOKEN:
        print("❌ ERROR: ADMIN_TOKEN not set in environment variables")
        print("Please set ADMIN_TOKEN in .env file or in this script")
        return False
    
    headers = {
        "Authorization": f"Bearer {ADMIN_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print(f"\n{'='*60}")
    print("TESTING TELEGRAM GROUP VERIFICATION")
    print(f"{'='*60}\n")
    
    # Test 1: Verify a valid group (replace TEST_GROUP_ID with real group)
    print(f"📝 Test 1: Verify Telegram Group")
    print(f"   Group ID: {TEST_GROUP_ID}")
    print(f"   Endpoint: GET /api/v1/telegram-groups/{TEST_GROUP_ID}/verify")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/telegram-groups/{TEST_GROUP_ID}/verify",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n   ✅ SUCCESS (200 OK)")
                print(f"   Response:")
                print(f"   - group_id: {data['group_id']}")
                print(f"   - group_name: {data['group_name']}")
                print(f"   - group_type: {data['group_type']}")
            else:
                print(f"\n   ❌ FAILED ({response.status_code})")
                print(f"   Error: {response.text}")
                
        except httpx.TimeoutException:
            print(f"\n   ❌ TIMEOUT - Request took too long")
            return False
        except Exception as e:
            print(f"\n   ❌ ERROR: {str(e)}")
            return False
    
    # Test 2: Try to verify an invalid group
    invalid_group_id = 999999999999
    print(f"\n{'-'*60}")
    print(f"📝 Test 2: Verify Invalid Group ID")
    print(f"   Group ID: {invalid_group_id}")
    print(f"   Expected: Should return error message")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/telegram-groups/{invalid_group_id}/verify",
                headers=headers
            )
            
            if response.status_code == 400:
                print(f"\n   ✅ CORRECT (400 Bad Request)")
                print(f"   Error message: {response.json()['detail']}")
            else:
                print(f"\n   ⚠️  UNEXPECTED ({response.status_code})")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"\n   ❌ ERROR: {str(e)}")
    
    # Test 3: Create group using the verified name
    print(f"\n{'-'*60}")
    print(f"📝 Test 3: Create Group with Verified Name")
    print(f"   Endpoint: POST /api/v1/telegram-groups")
    
    group_data = {
        "group_id": TEST_GROUP_ID,
        "group_name": "Test Group from Verify Endpoint"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # First, check if group already exists
            check_response = await client.get(
                f"{BASE_URL}/api/v1/telegram-groups",
                headers=headers
            )
            
            if check_response.status_code == 200:
                groups = check_response.json().get("groups", [])
                existing = any(g["group_id"] == TEST_GROUP_ID for g in groups)
                
                if existing:
                    print(f"   ⚠️  Group already exists, skipping create test")
                    print(f"   (Delete the group first to test create)")
                else:
                    # Create new group
                    response = await client.post(
                        f"{BASE_URL}/api/v1/telegram-groups",
                        headers=headers,
                        json=group_data
                    )
                    
                    if response.status_code == 201:
                        data = response.json()
                        print(f"\n   ✅ SUCCESS (201 Created)")
                        print(f"   Created group:")
                        print(f"   - group_id: {data['group_id']}")
                        print(f"   - group_name: {data['group_name']}")
                        print(f"   - is_active: {data['is_active']}")
                    elif response.status_code == 409:
                        print(f"\n   ⚠️  CONFLICT (409)")
                        print(f"   Group already exists in database")
                    else:
                        print(f"\n   ❌ FAILED ({response.status_code})")
                        print(f"   Error: {response.text}")
                        
        except Exception as e:
            print(f"\n   ❌ ERROR: {str(e)}")
    
    print(f"\n{'='*60}")
    print("TESTING COMPLETED")
    print(f"{'='*60}\n")


async def test_without_auth():
    """Test that endpoint rejects unauthenticated requests"""
    
    print(f"\n{'='*60}")
    print("TESTING AUTHENTICATION")
    print(f"{'='*60}\n")
    
    test_group_id = -1001234567890
    
    print(f"📝 Test: Verify without authentication")
    print(f"   Expected: Should return 401 Unauthorized")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/telegram-groups/{test_group_id}/verify"
            )
            
            if response.status_code == 401:
                print(f"\n   ✅ CORRECT (401 Unauthorized)")
                print(f"   Endpoint properly secured")
            else:
                print(f"\n   ❌ UNEXPECTED ({response.status_code})")
                print(f"   Expected 401, got {response.status_code}")
                
        except Exception as e:
            print(f"\n   ❌ ERROR: {str(e)}")


async def main():
    """Run all tests"""
    print("\n🧪 TELEGRAM GROUP VERIFICATION TEST SUITE")
    print("="*60)
    print("\nPrerequisites:")
    print("1. Set ADMIN_TOKEN in .env file or in this script")
    print("2. Set TEST_GROUP_ID to a valid Telegram group ID")
    print("3. Bot must be added to the test group")
    print("\n" + "="*60)
    
    # Check prerequisites
    if not ADMIN_TOKEN:
        print("\n⚠️  WARNING: ADMIN_TOKEN not set")
        print("Set it in .env file: ADMIN_TOKEN=your_token_here")
        print("Or modify this script directly")
        return
    
    if TEST_GROUP_ID == -1001234567890:
        print("\n⚠️  WARNING: TEST_GROUP_ID is still the default value")
        print("Replace it with a real Telegram group ID for testing")
        print("\nYou can get group ID by:")
        print("- Forward message from group to @userinfobot")
        print("- Or use @getidsbot in the group")
        print()
        
        response = input("Do you want to continue with test anyway? (y/n): ")
        if response.lower() != 'y':
            print("Testing cancelled.")
            return
    
    # Run authentication test first
    await test_without_auth()
    
    # Run main tests
    await test_verify_endpoint()


if __name__ == "__main__":
    asyncio.run(main())