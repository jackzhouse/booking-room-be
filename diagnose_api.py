"""
Diagnose API issues - test different endpoints to identify the problem
"""
import requests
import json

API_BASE_URL = "https://booking-room-be.onrender.com/api/v1"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2OTk3N2ZlNGIxZjZkNmIyNmVlZmU4YzQiLCJleHAiOjE3NzIxNDg3NTZ9.wTQ2kitGGOj1KXeOfcc4NRbr0F1VkRSyvAOwpPAFDls"

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

print("=" * 60)
print("DIAGNOSTIC REPORT - Booking Room API")
print("=" * 60)
print()

# Test 1: Health check
print("1. Health Check (no auth required):")
response = requests.get("https://booking-room-be.onrender.com/")
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    print(f"   ✅ Server is running")
    print(f"   Response: {response.json()}")
print()

# Test 2: Login endpoint
print("2. Testing Login (no auth required):")
login_response = requests.post(
    f"{API_BASE_URL}/auth/telegram",
    json={
        "init_data": "user=%7B%22id%22%3A293871670%2C%22first_name%22%3A%22Joko%22%2C%22last_name%22%3A%22Makruf%22%7D",
        "hash": "test_hash"
    }
)
print(f"   Status: {login_response.status_code}")
if login_response.status_code == 200:
    print(f"   ✅ Login endpoint works")
    print(f"   Response: {login_response.json()}")
else:
    print(f"   ❌ Login failed")
    print(f"   Response: {login_response.text}")
print()

# Test 3: Try without authentication
print("3. Testing GET /rooms WITHOUT authentication:")
response = requests.get(f"{API_BASE_URL}/rooms")
print(f"   Status: {response.status_code}")
if response.status_code == 401:
    print(f"   ✅ Correctly returns 401 (requires auth)")
elif response.status_code == 500:
    print(f"   ❌ 500 error - likely database or server issue")
    print(f"   Response: {response.text}")
else:
    print(f"   Response: {response.text}")
print()

# Test 4: Try with authentication
print("4. Testing GET /rooms WITH authentication:")
response = requests.get(f"{API_BASE_URL}/rooms", headers=headers)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    print(f"   ✅ Authentication works!")
    print(f"   Response: {json.dumps(response.json(), indent=4)}")
elif response.status_code == 500:
    print(f"   ❌ 500 error - database connection issue likely")
    print(f"   Response: {response.text}")
elif response.status_code == 401:
    print(f"   ❌ Token invalid or expired")
    print(f"   Response: {response.text}")
print()

# Test 5: Try to create room
print("5. Testing POST /rooms (create room - requires admin):")
room_data = {
    "name": "Test Room",
    "capacity": 5,
    "facilities": ["AC"],
    "location": "Test"
}
response = requests.post(
    f"{API_BASE_URL}/rooms",
    json=room_data,
    headers=headers
)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    print(f"   ✅ Room created successfully!")
    print(f"   Response: {json.dumps(response.json(), indent=4)}")
elif response.status_code == 403:
    print(f"   ❌ User is not an admin")
    print(f"   Response: {response.text}")
elif response.status_code == 500:
    print(f"   ❌ Server error - check server logs")
    print(f"   Response: {response.text}")
print()

print("=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
print()
print("If you see 500 errors, please:")
print("1. Check Render dashboard → Services → booking-room-be → Logs")
print("2. Look for error messages in the logs")
print("3. Common issues:")
print("   - Database connection failure")
print("   - Missing environment variables")
print("   - MongoDB Atlas connection string issues")