from datetime import datetime, timedelta
from typing import Dict, Any

from app.models.booking import Booking
from app.models.room import Room
from app.models.user import User
from app.core.config import settings


async def get_dashboard_statistics() -> Dict[str, Any]:
    """
    Get comprehensive dashboard statistics.
    
    Returns:
        Dictionary containing:
        - Booking statistics (today, this week, active)
        - Room statistics (total, active)
        - User statistics (total, active)
    """
    # Get current time in configured timezone (Asia/Jakarta)
    now = datetime.now(settings.timezone)
    
    # Calculate today's date range
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    # Calculate this week's date range (Monday to Sunday)
    weekday = now.weekday()  # Monday = 0, Sunday = 6
    week_start = (today_start - timedelta(days=weekday)).replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)
    
    # Query bookings for today (all statuses)
    bookings_today = await Booking.find({
        "start_time": {
            "$gte": today_start,
            "$lt": today_end
        }
    }).count()
    
    # Query bookings for this week (all statuses)
    bookings_this_week = await Booking.find({
        "start_time": {
            "$gte": week_start,
            "$lt": week_end
        }
    }).count()
    
    # Query active bookings for today
    active_bookings_today = await Booking.find({
        "status": "active",
        "start_time": {
            "$gte": today_start,
            "$lt": today_end
        }
    }).count()
    
    # Query active bookings for this week
    active_bookings_this_week = await Booking.find({
        "status": "active",
        "start_time": {
            "$gte": week_start,
            "$lt": week_end
        }
    }).count()
    
    # Query room statistics
    total_rooms = await Room.find().count()
    active_rooms = await Room.find({"is_active": True}).count()
    
    # Query user statistics
    total_users = await User.find().count()
    active_users = await User.find({"is_active": True}).count()
    
    return {
        "bookings_today": bookings_today,
        "bookings_this_week": bookings_this_week,
        "active_bookings_today": active_bookings_today,
        "active_bookings_this_week": active_bookings_this_week,
        "total_rooms": total_rooms,
        "active_rooms": active_rooms,
        "total_users": total_users,
        "active_users": active_users
    }