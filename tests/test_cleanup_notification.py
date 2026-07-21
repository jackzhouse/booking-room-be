"""
Test script for cleanup notification scheduler.
Tests the automatic notification for ended meetings.
"""
import asyncio
from datetime import datetime, timedelta
from bson import ObjectId

from app.core.config import settings
from app.core.database import connect_to_mongo, init_beanie_models
from app.models.booking import Booking, UserSnapshot, RoomSnapshot
from app.models.setting import Setting
from app.services.scheduler_service import check_and_notify_ended_bookings, get_pending_cleanup_count, get_recent_ended_bookings
from app.services.telegram_service import notify_verification_group_cleanup


async def test_cleanup_notification():
    """Test cleanup notification for ended bookings."""
    
    # Connect to database
    await connect_to_mongo()
    await init_beanie_models([Booking, Setting])
    
    print("=" * 70)
    print("🧪 TEST: Cleanup Notification Scheduler")
    print("=" * 70)
    
    # 1. Check current settings
    print("\n📋 STEP 1: Checking Settings")
    print("-" * 70)
    
    verification_group_setting = await Setting.find_one(Setting.key == "default_verification_group_id")
    if verification_group_setting:
        print(f"✅ Default Verification Group ID: {verification_group_setting.value}")
    else:
        print("❌ Default Verification Group ID not set!")
        print("   Please set it with: PUT /api/v1/admin/settings/default_verification_group_id")
        return
    
    try:
        verification_group_id = int(verification_group_setting.value)
    except (ValueError, TypeError):
        print("❌ Invalid verification group ID format!")
        return
    
    # 2. Check pending cleanup bookings
    print("\n📋 STEP 2: Checking Pending Cleanup Bookings")
    print("-" * 70)
    
    pending_count = await get_pending_cleanup_count()
    print(f"📊 Pending cleanup notifications: {pending_count}")
    
    recent_ended = await get_recent_ended_bookings(limit=5)
    if recent_ended:
        print(f"\n📋 Recent ended bookings (top 5):")
        for i, booking in enumerate(recent_ended, 1):
            status_icon = "✅" if booking.hrd_notified else "⏳"
            print(f"  {status_icon} {i}. {booking.booking_number} | {booking.room_snapshot.name}")
            print(f"     End Time: {booking.end_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            print(f"     HRD Notified: {booking.hrd_notified}")
            print(f"     Verification Group: {booking.verification_group_id}")
    else:
        print("📋 No ended bookings found.")
    
    # 3. Test with a dummy booking (optional)
    print("\n📋 STEP 3: Creating Test Booking (Optional)")
    print("-" * 70)
    
    create_test_booking = input("\n🤔 Do you want to create a test booking that ended 5 minutes ago? (y/n): ").lower().strip()
    
    if create_test_booking == 'y':
        now = datetime.now(settings.timezone)
        end_time = now - timedelta(minutes=5)
        start_time = end_time - timedelta(hours=1)
        
        test_booking = Booking(
            booking_number="TEST-99999",
            user_id=ObjectId("507f1f77bcf86cd799439011"),
            user_snapshot=UserSnapshot(
                full_name="Test User",
                username="testuser",
                division="IT",
                telegram_id=123456789
            ),
            room_id=ObjectId("507f1f77bcf86cd799439012"),
            room_snapshot=RoomSnapshot(name="Test Room"),
            telegram_group_id=verification_group_id,
            title="Test Cleanup Notification",
            division="IT",
            description="Test booking for cleanup notification",
            start_time=start_time,
            end_time=end_time,
            status="active",
            published=True,
            has_consumption=False,
            verification_group_id=verification_group_id,
            hrd_notified=False
        )
        
        await test_booking.insert()
        print(f"✅ Test booking created: {test_booking.booking_number}")
        print(f"   Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"   End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        # 4. Manually trigger scheduler for this booking
        print("\n📋 STEP 4: Manually Triggering Scheduler for Test Booking")
        print("-" * 70)
        
        print(f"⏳ Sending cleanup notification to group {verification_group_id}...")
        try:
            await notify_verification_group_cleanup(test_booking)
            print("✅ Cleanup notification sent successfully!")
            
            # Mark as notified
            test_booking.hrd_notified = True
            test_booking.updated_at = datetime.now(settings.timezone)
            await test_booking.save()
            print("✅ Test booking marked as notified")
            
        except Exception as e:
            print(f"❌ Error sending notification: {e}")
            print("   Possible reasons:")
            print("   - Bot not added to verification group")
            print("   - Invalid group ID")
            print("   - Network issues")
        
        # 5. Clean up test booking
        print("\n📋 STEP 5: Cleaning Up Test Booking")
        print("-" * 70)
        
        delete_test = input("\n🤔 Do you want to delete the test booking? (y/n): ").lower().strip()
        if delete_test == 'y':
            await test_booking.delete()
            print("✅ Test booking deleted")
    
    # 6. Test full scheduler function
    print("\n📋 STEP 6: Testing Full Scheduler Function")
    print("-" * 70)
    
    run_full_test = input("\n🤔 Do you want to run the full scheduler on ALL pending bookings? (y/n): ").lower().strip()
    
    if run_full_test == 'y':
        print(f"⏳ Running scheduler...")
        await check_and_notify_ended_bookings()
        print("✅ Scheduler completed")
        
        # Check again
        final_pending_count = await get_pending_cleanup_count()
        print(f"\n📊 Final pending cleanup notifications: {final_pending_count}")
        print(f"   Notifications sent: {pending_count - final_pending_count}")
    
    print("\n" + "=" * 70)
    print("✅ TEST COMPLETED")
    print("=" * 70)
    print("\n💡 Notes:")
    print("   - Scheduler runs automatically every 5 minutes")
    print("   - Check logs for scheduler output")
    print("   - Make sure bot is added to verification group")
    print("   - Verify verification_group_id is set in settings")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_cleanup_notification())