"""
Scheduler service for automatic background tasks.
Handles cleanup notifications for ended bookings.
"""
from datetime import datetime
from typing import List

from app.models.booking import Booking
from app.services.telegram_service import notify_verification_group_cleanup
from app.core.config import settings


async def check_and_notify_ended_bookings():
    """
    Check for ended bookings that haven't been notified for cleanup yet.
    
    This function should be called periodically (e.g., every 5 minutes).
    It finds active, published bookings where:
    - end_time is in the past
    - hrd_notified is False
    
    For each booking found, it:
    1. Sends cleanup notification to verification group
    2. Marks hrd_notified = True
    """
    print(f"[Scheduler] =======================================")
    print(f"[Scheduler] check_and_notify_ended_bookings() called")
    
    now = datetime.now(settings.timezone)
    print(f"[Scheduler] Current time (Asia/Jakarta): {now}")
    print(f"[Scheduler] settings.timezone: {settings.timezone}")
    print(f"[Scheduler] UTC now: {datetime.utcnow()}")
    
    # Find bookings that need cleanup notification
    query = {
        "status": "active",
        "published": True,
        "end_time": {"$lt": now},
        "hrd_notified": False
    }
    print(f"[Scheduler] Query: {query}")
    
    bookings = await Booking.find(query).to_list()
    
    print(f"[Scheduler] Found {len(bookings)} bookings needing cleanup notification")
    
    if not bookings:
        print(f"[Scheduler] No bookings to process")
        return
    
    for booking in bookings:
        print(f"[Scheduler] --------------------------------------")
        print(f"[Scheduler] Processing booking: {booking.booking_number}")
        print(f"[Scheduler]   - Room: {booking.room_snapshot.name}")
        print(f"[Scheduler]   - Start: {booking.start_time}")
        print(f"[Scheduler]   - End: {booking.end_time}")
        print(f"[Scheduler]   - Status: {booking.status}")
        print(f"[Scheduler]   - Published: {booking.published}")
        print(f"[Scheduler]   - HRD Notified: {booking.hrd_notified}")
        print(f"[Scheduler]   - Verification Group ID: {booking.verification_group_id}")
        
        try:
            # Send cleanup notification
            print(f"[Scheduler]   - Sending notification to verification group...")
            await notify_verification_group_cleanup(booking)
            
            # Mark as notified
            booking.hrd_notified = True
            booking.updated_at = now
            await booking.save()
            
            print(f"[Scheduler] ✓ Cleanup notification sent for booking {booking.booking_number}")
            print(f"[Scheduler] ✓ hrd_notified set to True")
            
        except Exception as e:
            print(f"[Scheduler] ✗ Error processing booking {booking.booking_number}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"[Scheduler] =======================================")


async def get_pending_cleanup_count() -> int:
    """
    Get count of bookings pending cleanup notification.
    
    Returns:
        Number of bookings that need cleanup notification
    """
    now = datetime.now(settings.timezone)
    
    count = await Booking.find({
        "status": "active",
        "published": True,
        "end_time": {"$lt": now},
        "hrd_notified": False
    }).count()
    
    return count


async def get_recent_ended_bookings(limit: int = 10) -> List[Booking]:
    """
    Get recently ended bookings (for monitoring/debugging).
    
    Args:
        limit: Maximum number of bookings to return
        
    Returns:
        List of recently ended bookings
    """
    now = datetime.now(settings.timezone)
    
    bookings = await Booking.find({
        "status": "active",
        "published": True,
        "end_time": {"$lt": now}
    }).sort(-Booking.end_time).limit(limit).to_list()
    
    return bookings