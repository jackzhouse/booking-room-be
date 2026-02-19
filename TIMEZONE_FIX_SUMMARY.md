# Timezone Fix for Auth Codes

## Problem
Auth code dates were stored in UTC in MongoDB but timezone conversion was inconsistent, causing verification errors. The system was failing to find valid codes due to timezone mismatches.

## Root Cause
1. MongoDB/Beanie stores timezone-aware datetimes as UTC
2. When retrieved, datetimes come back as naive (no timezone) UTC values
3. The previous timezone conversion logic was incomplete and inconsistent
4. This caused code verification to fail even for valid codes

## Solution Implemented

### 1. Added Helper Function (`app/services/auth_code_service.py`)
```python
def convert_utc_to_jakarta(dt: datetime) -> datetime:
    """
    Convert UTC datetime (naive or aware) to Jakarta timezone.
    
    Args:
        dt: Datetime object (can be naive UTC or aware)
    
    Returns:
        Datetime in Jakarta timezone
    """
    if dt.tzinfo is None:
        # Assume it's UTC and make it aware
        dt = dt.replace(tzinfo=timezone.utc)
    
    # Convert to Jakarta timezone
    return dt.astimezone(settings.timezone)
```

### 2. Updated `verify_code()` Method
- Uses `convert_utc_to_jakarta()` to consistently convert retrieved UTC datetimes to Jakarta timezone
- Updates `auth_code.expires_at` to Jakarta timezone for consistency
- All datetime comparisons now use Jakarta timezone

### 3. Updated `generate_code()` Method
- Generates codes with Jakarta timezone datetimes
- Returns Jakarta timezone `expires_at` for frontend display
- MongoDB automatically converts to UTC for storage

### 4. Updated `mark_code_used()` Method
- Stores `used_at` in Jakarta timezone
- MongoDB converts to UTC automatically

## Benefits
✅ All dates stored as UTC in MongoDB (database best practice)  
✅ Consistent timezone handling throughout the application  
✅ No more verification errors due to timezone mismatches  
✅ All datetime operations use Jakarta timezone for user-facing logic  
✅ All dates display in GMT+7 (Asia/Jakarta) timezone  

## Files Modified
- `app/services/auth_code_service.py` - Added timezone conversion helper and updated all datetime operations

## Testing
1. Generate a new auth code via `POST /api/v1/auth/generate-code`
2. Verify the code via `GET /api/v1/auth/verify-code?code={code}`
3. The code should be found and return "pending" status
4. All dates should display in Jakarta timezone (GMT+7)

## Note
The old code `805047` is already expired (created at 2026-02-19T22:46:38.032Z). You need to generate a new code to test the fix.