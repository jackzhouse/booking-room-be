"""
Check if user has admin privileges
"""
import requests

API_BASE_URL = "https://booking-room-be.onrender.com/api/v1"
ADMIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2OTk3N2ZlNGIxZjZkNmIyNmVlZmU4YzQiLCJleHAiOjE3NzIxNDg3NTZ9.wTQ2kitGGOj1KXeOfcc4NRbr0F1VkRSyvAOwpPAFDls"

def check_admin():
    """Try to access admin endpoint to check if user is admin."""
    headers = {
        "Authorization": f"Bearer {ADMIN_TOKEN}"
    }
    
    # Try to get admin settings (requires admin)
    response = requests.get(
        f"{API_BASE_URL}/admin/settings",
        headers=headers
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("\n✅ User is an admin!")
    elif response.status_code == 403:
        print("\n❌ User is NOT an admin. You need admin privileges to create rooms.")
    else:
        print(f"\n⚠️  Unexpected response: {response.status_code}")

if __name__ == "__main__":
    check_admin()