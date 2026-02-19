"""
Script to create sample rooms in the database.
Run this script to populate your MongoDB with initial room data.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import init_db
from app.models.room import Room
from datetime import datetime


async def create_sample_rooms():
    """Create sample rooms in the database."""
    
    # Initialize database connection
    await init_db()
    
    # Define sample rooms
    sample_rooms = [
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
    
    print("🚀 Starting sample room creation...\n")
    
    created_count = 0
    skipped_count = 0
    
    for room_data in sample_rooms:
        room_name = room_data["name"]
        
        # Check if room already exists
        existing_room = await Room.find_one(Room.name == room_name)
        
        if existing_room:
            print(f"⏭️  Room '{room_name}' already exists - skipping")
            skipped_count += 1
            continue
        
        # Create new room
        room = Room(**room_data)
        await room.insert()
        
        print(f"✅ Room '{room_name}' created successfully")
        print(f"   - Capacity: {room_data['capacity']} people")
        print(f"   - Location: {room_data['location']}")
        print(f"   - Facilities: {', '.join(room_data['facilities'])}\n")
        
        created_count += 1
    
    # Summary
    print("=" * 50)
    print(f"✨ Sample room creation completed!")
    print(f"   - Created: {created_count} rooms")
    print(f"   - Skipped: {skipped_count} rooms (already existed)")
    print("=" * 50)
    
    # Show all rooms
    all_rooms = await Room.find().sort(Room.name).to_list()
    print(f"\n📋 Total rooms in database: {len(all_rooms)}\n")
    
    for room in all_rooms:
        status = "✅ Active" if room.is_active else "❌ Inactive"
        print(f"   {status} {room.name} (Capacity: {room.capacity})")
    
    print()


if __name__ == "__main__":
    asyncio.run(create_sample_rooms())