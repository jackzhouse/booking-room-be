"""
Scheduler service for automatic background tasks.
Handles automatic completion and cleanup notifications for ended bookings.
"""
from datetime import datetime, timezone
from typing import List

from app.models.booking import Booking
from app.services.telegram_service import notify_verification_group_cleanup
from app.core.config import settings


async def _complete_booking(booking: Booking, now: datetime) -> bool:
    """
    Mark a booking as completed and send cleanup notification when needed.

    Returns:
        True if cleanup notification was sent successfully, otherwise False.
    """
    booking.status = "completed"
    booking.completed_at = booking.completed_at or now
    booking.updated_at = now
    await booking.save()

    if not booking.published or not booking.verification_group_id or booking.hrd_notified:
        return False

    await notify_verification_group_cleanup(booking)
    booking.hrd_notified = True
    booking.updated_at = datetime.now(settings.timezone)
    await booking.save()
    return True


async def check_and_notify_ended_bookings():
    """
    Check for ended bookings and auto-close them.
    
    This function should be called periodically (e.g., every 5 minutes).
    It finds active bookings whose end_time is in the past, marks them as
    completed, and sends cleanup notifications for published bookings.
    
    For each booking found, it:
    1. Marks booking status as completed
    2. Sends cleanup notification to verification group for published bookings
    3. Marks hrd_notified = True after cleanup notification is delivered
    """
    print(f"[Scheduler] =======================================")
    print(f"[Scheduler] check_and_notify_ended_bookings() called")
    
    now = datetime.now(settings.timezone)
    print(f"[Scheduler] Current time (Asia/Jakarta): {now}")
    print(f"[Scheduler] settings.timezone: {settings.timezone}")
    print(f"[Scheduler] UTC now: {datetime.now(timezone.utc)}")
    
    # Find active bookings that have ended and need to be closed.
    active_query = {
        "status": "active",
        "end_time": {"$lte": now},
    }
    print(f"[Scheduler] Active query: {active_query}")
    
    active_bookings = await Booking.find(active_query).to_list()
    pending_cleanup_query = {
        "status": "completed",
        "published": True,
        "end_time": {"$lte": now},
        "hrd_notified": False,
    }
    print(f"[Scheduler] Pending cleanup query: {pending_cleanup_query}")
    pending_cleanup_bookings = await Booking.find(pending_cleanup_query).to_list()

    booking_map = {str(booking.id): booking for booking in active_bookings}
    for booking in pending_cleanup_bookings:
        booking_map.setdefault(str(booking.id), booking)

    bookings = list(booking_map.values())

    print(f"[Scheduler] Found {len(bookings)} ended bookings to process")

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
            notification_sent = await _complete_booking(booking, now)

            if notification_sent:
                print(f"[Scheduler] ✓ Cleanup notification sent for booking {booking.booking_number}")
                print(f"[Scheduler] ✓ Booking marked as completed")
            else:
                print(f"[Scheduler] ✓ Booking marked as completed")
                print(f"[Scheduler] ✓ No cleanup notification needed")
            
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
        "status": {"$in": ["active", "completed"]},
        "published": True,
        "end_time": {"$lte": now},
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
        "status": {"$in": ["active", "completed"]},
        "end_time": {"$lte": now}
    }).sort(-Booking.end_time).limit(limit).to_list()

    return bookings
