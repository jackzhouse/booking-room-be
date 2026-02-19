"""
Create sample rooms using API calls.
This script doesn't require local database connection - it uses the production API.
"""
import requests

API_BASE_URL = "https://booking-room-be.onrender.com/api/v1"

# You need to provide your admin JWT token
# Get it by logging in as admin in your frontend
ADMIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2OTk3N2ZlNGIxZjZkNmIyNmVlZmU4YzQiLCJleHAiOjE3NzIxNDg3NTh9.MJgaXgVmJVWR0HVWSbr_xqlDSbk6fp3oAMcG2Mq3AtE"

# Sample rooms data
rooms = [
    {
        "name": "Ruang Meeting",
        "capacity": 10,
        "facilities": ["AC", "WiFi", "Projector", "Whiteboard"],
        "location": "Lantai 2",
        "is_active": True
    },
    {
        "name": "Ruang Emphaty",
        "capacity": 6,
        "facilities": ["AC", "WiFi", "Whiteboard"],
        "location": "Lantai 1",
        "is_active": True
    },
    {
        "name": "Ruang Mushola",
        "capacity": 30,
        "facilities": ["AC", "Speaker", "Karpet"],
        "location": "Lantai 3",
        "is_active": True
    }
]

def create_room(room_data):
    """Create a room via API."""
    headers = {
        "Authorization": f"Bearer {ADMIN_TOKEN}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{API_BASE_URL}/rooms",
        json=room_data,
        headers=headers
    )
    
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 403:
        print(f"Error creating room: 403 Forbidden - You don't have admin privileges")
        print(f"Response: {response.text}")
        return None
    else:
        print(f"Error creating room: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def main():
    """Create all sample rooms."""
    print("🚀 Creating sample rooms via API...\n")
    
    # First, check if rooms already exist
    headers = {
        "Authorization": f"Bearer {ADMIN_TOKEN}"
    }
    
    response = requests.get(
        f"{API_BASE_URL}/rooms",
        headers=headers
    )
    
    if response.status_code == 200:
        existing_rooms = response.json()
        existing_names = [room["name"] for room in existing_rooms]
        
        print(f"Found {len(existing_rooms)} existing rooms:")
        for room in existing_rooms:
            status = "✅" if room["is_active"] else "❌"
            print(f"   {status} {room['name']} (Capacity: {room['capacity']})")
        print()
    else:
        existing_names = []
        print("Could not fetch existing rooms\n")
    
    # Create rooms
    created_count = 0
    skipped_count = 0
    
    for room_data in rooms:
        room_name = room_data["name"]
        
        if room_name in existing_names:
            print(f"⏭️  Room '{room_name}' already exists - skipping")
            skipped_count += 1
            continue
        
        print(f"Creating room: {room_name}")
        result = create_room(room_data)
        
        if result:
            print(f"   ✅ Room '{room_name}' created successfully")
            print(f"   - Capacity: {room_data['capacity']} people")
            print(f"   - Location: {room_data['location']}")
            print(f"   - Facilities: {', '.join(room_data['facilities'])}\n")
            created_count += 1
    
    # Summary
    print("=" * 50)
    print(f"✨ Room creation completed!")
    print(f"   - Created: {created_count} rooms")
    print(f"   - Skipped: {skipped_count} rooms (already existed)")
    print("=" * 50)

if __name__ == "__main__":
    # Check if token is set
    if ADMIN_TOKEN == "YOUR_ADMIN_JWT_TOKEN_HERE":
        print("⚠️  Please set your admin JWT token in this script")
        print("   Edit line 8: ADMIN_TOKEN = 'your_actual_token_here'")
        print("\nTo get your admin token:")
        print("1. Log in as admin in your frontend")
        print("2. Get the JWT token from localStorage or network tab")
        print("3. Paste it in this script")
    else:
        main()