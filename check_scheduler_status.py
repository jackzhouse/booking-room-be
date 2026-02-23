"""
Check scheduler status and pending cleanup notifications.
This script checks which bookings need cleanup notification.
"""
import asyncio
from datetime import datetime

from app.core.config import settings
from app.core.database import connect_to_mongo, init_beanie_models
from app.models.booking import Booking


async def check_scheduler_status():
    """Check scheduler status and pending notifications."""
    
    # Connect to database
    await connect_to_mongo()
    await init_beanie_models([Booking])
    
    print("=" * 80)
    print("📊 SCHEDULER STATUS CHECK")
    print("=" * 80)
    
    now = datetime.now(settings.timezone)
    
    # Find pending cleanup bookings
    print("\n🔍 Finding bookings that need cleanup notification...")
    print("-" * 80)
    
    pending_bookings = await Booking.find({
        "status": "active",
        "published": True,
        "end_time": {"$lt": now},
        "hrd_notified": False
    }).sort(-Booking.end_time).to_list()
    
    print(f"\n📊 Total pending cleanup notifications: {len(pending_bookings)}")
    
    if pending_bookings:
        print(f"\n📋 List of bookings needing cleanup notification:")
        print("-" * 80)
        
        for i, booking in enumerate(pending_bookings, 1):
            ended_ago = now - booking.end_time
            
            print(f"\n  {i}. Booking: {booking.booking_number}")
            print(f"     Room: {booking.room_snapshot.name}")
            print(f"     Title: {booking.title}")
            print(f"     End Time: {booking.end_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            print(f"     Ended: {ended_ago.total_seconds() / 60:.0f} minutes ago")
            print(f"     Verification Group: {booking.verification_group_id}")
            print(f"     Status: {booking.status}")
            print(f"     Published: {booking.published}")
            print(f"     HRD Notified: {booking.hrd_notified}")
    else:
        print("\n✅ No bookings pending cleanup notification!")
    
    # Check recent notified bookings
    print(f"\n\n📋 Recently notified bookings (top 5):")
    print("-" * 80)
    
    notified_bookings = await Booking.find({
        "status": "active",
        "published": True,
        "end_time": {"$lt": now},
        "hrd_notified": True
    }).sort(-Booking.end_time).limit(5).to_list()
    
    if notified_bookings:
        for i, booking in enumerate(notified_bookings, 1):
            ended_ago = now - booking.end_time
            print(f"\n  {i}. Booking: {booking.booking_number}")
            print(f"     Room: {booking.room_snapshot.name}")
            print(f"     End Time: {booking.end_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            print(f"     Ended: {ended_ago.total_seconds() / 60:.0f} minutes ago")
            print(f"     HRD Notified: ✅")
    else:
        print("  No notified bookings found.")
    
    print("\n" + "=" * 80)
    print("✅ CHECK COMPLETED")
    print("=" * 80)
    print("\n💡 Notes:")
    print("   - Scheduler runs every 5 minutes")
    print("   - Pending bookings will receive notification on next scheduler run")
    print("   - Make sure verification_group_id is set correctly")
    print("   - Make sure bot is added to verification group")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(check_scheduler_status())