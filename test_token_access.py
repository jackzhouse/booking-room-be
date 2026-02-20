"""
Test if JWT token is valid and has admin access
"""
import requests

API_BASE_URL = "https://booking-room-be.onrender.com/api/v1"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2OTk3N2ZlNGIxZjZkNmIyNmVlZmU4YzQiLCJleHAiOjE3NzIxNDg3NTZ9.wTQ2kitGGOj1KXeOfcc4NRbr0F1VkRSyvAOwpPAFDls"

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

print("Testing API access...\n")

# Test 1: Get rooms (requires active user)
print("1. Testing GET /rooms (requires active user):")
response = requests.get(f"{API_BASE_URL}/rooms", headers=headers)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    print(f"   ✅ Token is valid and user is active")
    rooms = response.json()
    print(f"   Found {len(rooms)} rooms")
else:
    print(f"   ❌ Response: {response.text}")

print()

# Test 2: Try admin endpoint
print("2. Testing GET /admin/settings (requires admin):")
response = requests.get(f"{API_BASE_URL}/admin/settings", headers=headers)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    print(f"   ✅ User has admin privileges")
    print(f"   Response: {response.json()}")
elif response.status_code == 403:
    print(f"   ❌ User does NOT have admin privileges")
    print(f"   Response: {response.text}")
else:
    print(f"   ⚠️  Unexpected response: {response.text}")