#!/usr/bin/env python3
"""
Database Migration: Convert Device Ownership to Device Bookmarks

This migration script converts the current device ownership model to a bookmark/favorites system
where:
1. Devices are global (no ownership)
2. Teachers can bookmark devices for easy access
3. Multiple teachers can bookmark the same device
4. Removing a bookmark doesn't delete the device

Migration Steps:
1. Create new device_bookmarks table
2. Migrate existing device-user relationships to bookmarks
3. Remove user_id column from devices table
4. Update unique constraints
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text, MetaData, Table, Column, String, DateTime, Boolean, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from constants import DB_HOSTNAME, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE

# Database connection
# Extract hostname from DB_HOSTNAME (remove protocol and port if present)
hostname = DB_HOSTNAME.replace('http://', '').replace('https://', '').split(':')[0]
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{hostname}:{DB_PORT}/{DB_DATABASE}"

def run_migration():
    """Run the device bookmark migration."""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        
        try:
            print("Starting device bookmark migration...")
            
            # Step 1: Create device_bookmarks table
            print("1. Creating device_bookmarks table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS device_bookmarks (
                    id VARCHAR(36) PRIMARY KEY,
                    device_id VARCHAR(36) NOT NULL,
                    user_id VARCHAR(64) NOT NULL,
                    nickname VARCHAR(50) NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE,
                    UNIQUE KEY unique_user_device_bookmark (user_id, device_id),
                    UNIQUE KEY unique_user_nickname (user_id, nickname)
                )
            """))
            
            # Step 2: Migrate existing device-user relationships to bookmarks
            print("2. Migrating existing device ownership to bookmarks...")
            conn.execute(text("""
                INSERT INTO device_bookmarks (id, device_id, user_id, nickname, created_at, updated_at)
                SELECT 
                    UUID() as id,
                    id as device_id,
                    user_id,
                    nickname,
                    created_at,
                    updated_at
                FROM devices 
                WHERE user_id IS NOT NULL
            """))
            
            # Step 3: Remove foreign key constraint first
            print("3. Removing foreign key constraint from devices table...")
            try:
                conn.execute(text("ALTER TABLE devices DROP FOREIGN KEY devices_ibfk_1"))
            except Exception as e:
                print(f"   Note: devices_ibfk_1 constraint may not exist: {e}")
            
            # Step 4: Remove unique constraint on user_id + nickname from devices table
            print("4. Removing unique constraint from devices table...")
            try:
                conn.execute(text("ALTER TABLE devices DROP INDEX unique_nickname_per_user"))
            except Exception as e:
                print(f"   Note: unique_nickname_per_user constraint may not exist: {e}")
            
            # Step 5: Remove user_id column from devices table
            print("5. Removing user_id column from devices table...")
            conn.execute(text("ALTER TABLE devices DROP COLUMN user_id"))
            
            # Step 6: Update any remaining constraints or indexes
            print("6. Updating table structure...")
            
            # Commit the transaction
            trans.commit()
            print("✅ Migration completed successfully!")
            
            # Verify the migration
            print("\n7. Verifying migration...")
            result = conn.execute(text("SELECT COUNT(*) as device_count FROM devices"))
            device_count = result.fetchone()[0]
            
            result = conn.execute(text("SELECT COUNT(*) as bookmark_count FROM device_bookmarks"))
            bookmark_count = result.fetchone()[0]
            
            print(f"   Devices in system: {device_count}")
            print(f"   Device bookmarks: {bookmark_count}")
            
            if bookmark_count > 0:
                print("✅ Migration verification successful!")
            else:
                print("⚠️  No bookmarks found - this may be expected if no devices were previously registered")
                
        except Exception as e:
            # Rollback on error
            trans.rollback()
            print(f"❌ Migration failed: {e}")
            raise

def rollback_migration():
    """Rollback the device bookmark migration."""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        trans = conn.begin()
        
        try:
            print("Rolling back device bookmark migration...")
            
            # Step 1: Add user_id column back to devices table
            print("1. Adding user_id column back to devices table...")
            conn.execute(text("ALTER TABLE devices ADD COLUMN user_id VARCHAR(64)"))
            
            # Step 2: Migrate bookmarks back to device ownership
            print("2. Migrating bookmarks back to device ownership...")
            conn.execute(text("""
                UPDATE devices d
                JOIN device_bookmarks db ON d.id = db.device_id
                SET d.user_id = db.user_id
                WHERE db.id = (
                    SELECT db2.id 
                    FROM device_bookmarks db2 
                    WHERE db2.device_id = d.id 
                    ORDER BY db2.created_at ASC 
                    LIMIT 1
                )
            """))
            
            # Step 3: Add foreign key constraint
            print("3. Adding foreign key constraint...")
            conn.execute(text("ALTER TABLE devices ADD FOREIGN KEY (user_id) REFERENCES user(user_id)"))
            
            # Step 4: Add unique constraint
            print("4. Adding unique constraint...")
            conn.execute(text("ALTER TABLE devices ADD CONSTRAINT unique_nickname_per_user UNIQUE (user_id, nickname)"))
            
            # Step 5: Drop device_bookmarks table
            print("5. Dropping device_bookmarks table...")
            conn.execute(text("DROP TABLE IF EXISTS device_bookmarks"))
            
            trans.commit()
            print("✅ Rollback completed successfully!")
            
        except Exception as e:
            trans.rollback()
            print(f"❌ Rollback failed: {e}")
            raise

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Device Bookmark Migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    
    args = parser.parse_args()
    
    if args.rollback:
        rollback_migration()
    else:
        run_migration()
