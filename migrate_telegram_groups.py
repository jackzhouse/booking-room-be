"""
Migration script to migrate telegram_group_id from settings to TelegramGroup model.

This script:
1. Reads the existing telegram_group_id from settings
2. Creates a TelegramGroup entry with that ID
3. Leaves the setting for backward compatibility (can be removed later)

Usage:
    python migrate_telegram_groups.py
"""

import asyncio
import sys
from app.core.database import connect_to_mongo, close_mongo_connection, init_beanie_models
from app.models.setting import Setting
from app.models.telegram_group import TelegramGroup


async def migrate():
    """Migrate telegram_group_id from settings to TelegramGroup model."""
    print("🔄 Starting Telegram Groups migration...")
    
    # Connect to MongoDB
    await connect_to_mongo()
    print("✅ Connected to MongoDB")
    
    # Initialize Beanie
    await init_beanie_models([Setting, TelegramGroup])
    print("✅ Initialized Beanie models")
    
    # Get existing telegram_group_id from settings
    setting = await Setting.find_one(Setting.key == "telegram_group_id")
    
    if not setting:
        print("⚠️  No telegram_group_id found in settings")
        print("   Nothing to migrate.")
        await close_mongo_connection()
        return
    
    group_id_str = setting.value.strip()
    
    if not group_id_str:
        print("⚠️  telegram_group_id setting is empty")
        print("   Nothing to migrate.")
        await close_mongo_connection()
        return
    
    try:
        group_id = int(group_id_str)
    except ValueError:
        print(f"❌ Invalid telegram_group_id value: {group_id_str}")
        print("   Must be a valid integer.")
        await close_mongo_connection()
        sys.exit(1)
    
    # Check if group already exists
    existing = await TelegramGroup.find_one(TelegramGroup.group_id == group_id)
    
    if existing:
        print(f"⚠️  TelegramGroup with ID {group_id} already exists")
        print("   Skipping migration.")
        await close_mongo_connection()
        return
    
    # Create TelegramGroup entry
    telegram_group = TelegramGroup(
        group_id=group_id,
        group_name="Migrated from Settings",  # Admin can update this later
        is_active=True
    )
    await telegram_group.insert()
    
    print(f"✅ Successfully migrated Telegram group:")
    print(f"   Group ID: {group_id}")
    print(f"   Group Name: {telegram_group.group_name}")
    print(f"   Status: Active")
    
    # Note: We keep the setting for backward compatibility
    # Old bookings that were created before migration won't have telegram_group_id field
    # The setting can be removed later after all bookings are updated
    
    print("\n📝 Migration completed!")
    print("⚠️  Note: Old bookings (created before this migration) don't have telegram_group_id.")
    print("   You may want to:")
    print("   1. Update old bookings manually, OR")
    print("   2. Remove the telegram_group_id setting after all bookings are updated")
    
    await close_mongo_connection()
    print("\n✅ Disconnected from MongoDB")


if __name__ == "__main__":
    asyncio.run(migrate())