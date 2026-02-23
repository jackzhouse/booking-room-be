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
    now = datetime.now(settings.timezone)
    
    # Find bookings that need cleanup notification
    bookings = await Booking.find({
        "status": "active",
        "published": True,
        "end_time": {"$lt": now},
        "hrd_notified": False
    }).to_list()
    
    if not bookings:
        return
    
    print(f"[Scheduler] Found {len(bookings)} bookings needing cleanup notification")
    
    for booking in bookings:
        try:
            # Send cleanup notification
            await notify_verification_group_cleanup(booking)
            
            # Mark as notified
            booking.hrd_notified = True
            booking.updated_at = now
            await booking.save()
            
            print(f"[Scheduler] Cleanup notification sent for booking {booking.booking_number}")
            
        except Exception as e:
            print(f"[Scheduler] Error processing booking {booking.booking_number}: {e}")


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