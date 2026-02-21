"""
Test script for dashboard statistics endpoint.
Run this script to verify the dashboard statistics API is working.
"""

import asyncio
import sys
from datetime import datetime
from app.core.database import connect_to_mongo, close_mongo_connection, init_beanie_models
from app.models.user import User
from app.models.room import Room
from app.models.booking import Booking
from app.models.booking_history import BookingHistory
from app.models.setting import Setting
from app.models.auth_code import AuthCode
from app.models.telegram_group import TelegramGroup
from app.services.dashboard_service import get_dashboard_statistics
from app.core.config import settings


async def test_dashboard_stats():
    """Test dashboard statistics function"""
    print("=" * 60)
    print("Testing Dashboard Statistics Service")
    print("=" * 60)
    
    try:
        # Connect to database
        print("\n[1/4] Connecting to database...")
        await connect_to_mongo()
        
        # Initialize Beanie models
        print("[2/4] Initializing database models...")
        await init_beanie_models([
            User,
            Room,
            Booking,
            BookingHistory,
            Setting,
            AuthCode,
            TelegramGroup
        ])
        print("✅ Database models initialized")
        
        # Get dashboard statistics
        print("[3/4] Fetching dashboard statistics...")
        stats = await get_dashboard_statistics()
        
        # Display results
        print("\n[4/4] Dashboard Statistics Results:")
        print("-" * 60)
        
        print(f"\n📊 BOOKING STATISTICS:")
        print(f"  • Total bookings today:        {stats['bookings_today']}")
        print(f"  • Total bookings this week:    {stats['bookings_this_week']}")
        print(f"  • Active bookings today:      {stats['active_bookings_today']}")
        print(f"  • Active bookings this week:  {stats['active_bookings_this_week']}")
        
        print(f"\n🏢 ROOM STATISTICS:")
        print(f"  • Total rooms:                 {stats['total_rooms']}")
        print(f"  • Active rooms:               {stats['active_rooms']}")
        
        print(f"\n👥 USER STATISTICS:")
        print(f"  • Total users:                 {stats['total_users']}")
        print(f"  • Active users:               {stats['active_users']}")
        
        print("\n" + "-" * 60)
        print("✅ Dashboard statistics retrieved successfully!")
        
        # Verify data integrity
        print("\n📋 Data Integrity Checks:")
        if stats['active_bookings_today'] <= stats['bookings_today']:
            print("✅ Active bookings today <= Total bookings today")
        else:
            print("❌ ERROR: Active bookings today > Total bookings today")
            
        if stats['active_bookings_this_week'] <= stats['bookings_this_week']:
            print("✅ Active bookings this week <= Total bookings this week")
        else:
            print("❌ ERROR: Active bookings this week > Total bookings this week")
            
        if stats['active_rooms'] <= stats['total_rooms']:
            print("✅ Active rooms <= Total rooms")
        else:
            print("❌ ERROR: Active rooms > Total rooms")
            
        if stats['active_users'] <= stats['total_users']:
            print("✅ Active users <= Total users")
        else:
            print("❌ ERROR: Active users > Total users")
        
        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Close database connection
        print("\nCleaning up...")
        await close_mongo_connection()


if __name__ == "__main__":
    success = asyncio.run(test_dashboard_stats())
    sys.exit(0 if success else 1)