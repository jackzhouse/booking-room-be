from pydantic import BaseModel, ConfigDict


class DashboardStats(BaseModel):
    """Dashboard statistics response"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "bookings_today": 15,
                "bookings_this_week": 87,
                "active_bookings_today": 12,
                "active_bookings_this_week": 75,
                "total_rooms": 5,
                "active_rooms": 4,
                "total_users": 42,
                "active_users": 40
            }
        }
    )
    
    # Booking statistics
    bookings_today: int
    bookings_this_week: int
    active_bookings_today: int
    active_bookings_this_week: int
    
    # Room statistics
    total_rooms: int
    active_rooms: int
    
    # User statistics
    total_users: int
    active_users: int
    
