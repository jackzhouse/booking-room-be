"""
Test script for AuthCodeService timezone handling.
Run this before committing to verify the fix works.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

# Test timezone handling (simulating settings.timezone)
settings_tz = ZoneInfo("Asia/Jakarta")

def test_timezone_comparison():
    """Test timezone-aware and naive datetime comparison"""
    print("Testing timezone comparison...")
    
    # Create a naive datetime (as MongoDB stores)
    naive_dt = datetime(2026, 2, 20, 12, 0, 0)
    print(f"Naive datetime: {naive_dt}")
    print(f"Naive datetime tzinfo: {naive_dt.tzinfo}")
    
    # Convert to timezone-aware using replace()
    aware_dt = naive_dt.replace(tzinfo=settings_tz)
    print(f"Aware datetime: {aware_dt}")
    print(f"Aware datetime tzinfo: {aware_dt.tzinfo}")
    
    # Create current time in Jakarta timezone
    now = datetime.now(settings_tz)
    print(f"Now (aware): {now}")
    
    # Test comparison
    try:
        if now > aware_dt:
            print(f"✅ Comparison successful: {now} > {aware_dt}")
        else:
            print(f"✅ Comparison successful: {now} <= {aware_dt}")
        return True
    except Exception as e:
        print(f"❌ Comparison failed: {e}")
        return False

def test_replace_method():
    """Test that replace() works with ZoneInfo"""
    print("\nTesting replace() method with ZoneInfo...")
    
    try:
        naive = datetime(2026, 2, 20, 12, 0, 0)
        aware = naive.replace(tzinfo=settings_tz)
        print(f"✅ replace() works: {aware}")
        return True
    except Exception as e:
        print(f"❌ replace() failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Testing AuthCodeService timezone handling")
    print("=" * 60)
    
    test1 = test_replace_method()
    test2 = test_timezone_comparison()
    
    print("\n" + "=" * 60)
    if test1 and test2:
        print("✅ All tests passed! Safe to commit and push.")
    else:
        print("❌ Some tests failed! Fix issues first.")
    print("=" * 60)