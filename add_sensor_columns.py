#!/usr/bin/env python3
"""
Database Migration: Add new sensor columns to device_data table

This migration script adds two new sensor columns to the device_data table:
1. thermometer - Thermometer reading in Celsius (from different sensor)
2. moisture - Soil moisture percentage (from soil meter)

Both columns are nullable as not all sensors may be plugged in for each reading.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from constants import DB_HOSTNAME, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE

# Database connection
# Extract hostname from DB_HOSTNAME (remove protocol and port if present)
hostname = DB_HOSTNAME.replace('http://', '').replace('https://', '').split(':')[0]
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{hostname}:{DB_PORT}/{DB_DATABASE}"

def run_migration():
    """Add new sensor columns to device_data table."""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        
        try:
            print("Starting sensor columns migration...")
            
            # Check if columns already exist
            print("1. Checking existing columns...")
            result = conn.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'device_data' 
                AND COLUMN_NAME IN ('thermometer', 'moisture')
            """))
            existing_columns = [row[0] for row in result.fetchall()]
            
            # Add thermometer column if it doesn't exist
            if 'thermometer' not in existing_columns:
                print("2. Adding thermometer column...")
                conn.execute(text("""
                    ALTER TABLE device_data 
                    ADD COLUMN thermometer DECIMAL(5, 2) NULL 
                    COMMENT 'Thermometer reading in Celsius'
                """))
                print("   ✅ thermometer column added")
            else:
                print("   ⚠️  thermometer column already exists")
            
            # Add moisture column if it doesn't exist
            if 'moisture' not in existing_columns:
                print("3. Adding moisture column...")
                conn.execute(text("""
                    ALTER TABLE device_data 
                    ADD COLUMN moisture DECIMAL(5, 2) NULL 
                    COMMENT 'Soil moisture percentage'
                """))
                print("   ✅ moisture column added")
            else:
                print("   ⚠️  moisture column already exists")
            
            # Commit the transaction
            trans.commit()
            print("✅ Migration completed successfully!")
            
            # Verify the migration
            print("\n4. Verifying migration...")
            result = conn.execute(text("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_COMMENT
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'device_data'
                AND COLUMN_NAME IN ('temperature', 'thermometer', 'humidity', 'moisture', 'light', 'sound')
                ORDER BY ORDINAL_POSITION
            """))
            
            print("   Current sensor columns:")
            for row in result.fetchall():
                print(f"     {row[0]}: {row[1]} (nullable: {row[2]}) - {row[3]}")
                
        except Exception as e:
            # Rollback on error
            trans.rollback()
            print(f"❌ Migration failed: {e}")
            raise

def rollback_migration():
    """Rollback the sensor columns migration."""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        trans = conn.begin()
        
        try:
            print("Rolling back sensor columns migration...")
            
            # Remove thermometer column
            print("1. Removing thermometer column...")
            try:
                conn.execute(text("ALTER TABLE device_data DROP COLUMN thermometer"))
                print("   ✅ thermometer column removed")
            except Exception as e:
                print(f"   ⚠️  Could not remove thermometer column: {e}")
            
            # Remove moisture column
            print("2. Removing moisture column...")
            try:
                conn.execute(text("ALTER TABLE device_data DROP COLUMN moisture"))
                print("   ✅ moisture column removed")
            except Exception as e:
                print(f"   ⚠️  Could not remove moisture column: {e}")
            
            trans.commit()
            print("✅ Rollback completed successfully!")
            
        except Exception as e:
            trans.rollback()
            print(f"❌ Rollback failed: {e}")
            raise

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Sensor Columns Migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    
    args = parser.parse_args()
    
    if args.rollback:
        rollback_migration()
    else:
        run_migration()


