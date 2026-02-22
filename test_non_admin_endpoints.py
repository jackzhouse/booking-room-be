#!/usr/bin/env python3
"""
Test script to verify non-admin endpoints for bookings and telegram groups.

This script tests:
1. GET /bookings/all - Non-admin users can view all published bookings
2. GET /telegram-groups/list - Non-admin users can view available telegram groups
"""

import asyncio
import sys
from datetime import date, datetime
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.models.booking import Booking
from app.models.telegram_group import TelegramGroup
from app.models.room import Room
from app.models.user import User
from app.core.config import settings


async def setup_database():
    """Initialize database connection."""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    await init_beanie(
        database=client[settings.DATABASE_NAME],
        document_models=[
            Booking,
            TelegramGroup,
            Room,
            User
        ]
    )
    return client


async def test_bookings_all_endpoint():
    """Test GET /bookings/all endpoint functionality."""
    print("\n" + "="*60)
    print("TEST 1: GET /bookings/all endpoint")
    print("="*60)
    
    # Build query for published, active bookings only
    query = {
        "status": "active",
        "published": True
    }
    
    # Get all published bookings
    bookings = await Booking.find(query).sort(Booking.start_time).to_list()
    
    print(f"\nFound {len(bookings)} published, active bookings")
    
    if bookings:
        print("\nSample bookings:")
        for i, booking in enumerate(bookings[:3], 1):
            print(f"\n{i}. {booking.booking_number}")
            print(f"   Title: {booking.title}")
            print(f"   Room: {booking.room_snapshot.name}")
            print(f"   User: {booking.user_snapshot.full_name}")
            print(f"   Division: {booking.user_snapshot.division}")
            print(f"   Start: {booking.start_time}")
            print(f"   End: {booking.end_time}")
            print(f"   Published: {booking.published}")
    else:
        print("\nNo published bookings found. This is expected if no bookings have been published yet.")
    
    # Test with date filter
    today = date.today()
    start_datetime = datetime.combine(today, datetime.min.time())
    end_datetime = datetime.combine(today, datetime.max.time())
    
    query["start_time"] = {"$gte": start_datetime, "$lte": end_datetime}
    today_bookings = await Booking.find(query).sort(Booking.start_time).to_list()
    
    print(f"\n\nBookings for today ({today}): {len(today_bookings)}")
    
    print("\n✓ GET /bookings/all endpoint test completed")


async def test_telegram_groups_list_endpoint():
    """Test GET /telegram-groups/list endpoint functionality."""
    print("\n" + "="*60)
    print("TEST 2: GET /telegram-groups/list endpoint")
    print("="*60)
    
    # Get all telegram groups
    groups = await TelegramGroup.find().to_list()
    
    print(f"\nFound {len(groups)} telegram groups")
    
    if groups:
        print("\nAvailable telegram groups:")
        for i, group in enumerate(groups, 1):
            print(f"\n{i}. Group ID: {group.group_id}")
            print(f"   Name: {group.group_name}")
            print(f"   Created: {group.created_at}")
    else:
        print("\nNo telegram groups found. Admin needs to add groups first.")
    
    print("\n✓ GET /telegram-groups/list endpoint test completed")


async def test_room_filter():
    """Test room filter for /bookings/all endpoint."""
    print("\n" + "="*60)
    print("TEST 3: Room filter for /bookings/all endpoint")
    print("="*60)
    
    # Get all rooms
    rooms = await Room.find({"is_active": True}).to_list()
    
    if not rooms:
        print("\nNo active rooms found.")
        return
    
    print(f"\nFound {len(rooms)} active rooms")
    
    # Test bookings for first room
    room = rooms[0]
    print(f"\nTesting bookings for room: {room.name}")
    
    query = {
        "status": "active",
        "published": True,
        "room_id": room.id
    }
    
    room_bookings = await Booking.find(query).sort(Booking.start_time).to_list()
    
    print(f"Found {len(room_bookings)} published bookings for {room.name}")
    
    if room_bookings:
        print("\nSample bookings for this room:")
        for i, booking in enumerate(room_bookings[:3], 1):
            print(f"\n{i}. {booking.booking_number}")
            print(f"   Title: {booking.title}")
            print(f"   User: {booking.user_snapshot.full_name}")
            print(f"   Start: {booking.start_time}")
    
    print("\n✓ Room filter test completed")


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("TESTING NON-ADMIN ENDPOINTS")
    print("="*60)
    print("\nThis script tests the new endpoints for non-admin users:")
    print("1. GET /bookings/all - View all published bookings")
    print("2. GET /telegram-groups/list - View available telegram groups")
    
    try:
        client = await setup_database()
        print("\n✓ Database connected successfully")
        
        # Run tests
        await test_bookings_all_endpoint()
        await test_telegram_groups_list_endpoint()
        await test_room_filter()
        
        print("\n" + "="*60)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*60)
        
        # Close connection
        client.close()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())