#!/usr/bin/env python3
"""
Migration script to move PIN codes from class table to user table
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from db.init_engine import engine
from db import db_models

def migrate_student_pin():
    """Move PIN codes from class table to user table"""
    print("🔄 Migrating PIN codes from class to user table...")
    
    with engine.connect() as conn:
        # Add PIN fields to user table
        try:
            conn.execute(text("ALTER TABLE user ADD COLUMN pin_code VARCHAR(4) NULL"))
            print("✅ Added pin_code column to user table")
        except Exception as e:
            print(f"⚠️  pin_code column might already exist: {e}")
        
        try:
            conn.execute(text("ALTER TABLE user ADD COLUMN pin_reset_required BOOLEAN DEFAULT FALSE"))
            print("✅ Added pin_reset_required column to user table")
        except Exception as e:
            print(f"⚠️  pin_reset_required column might already exist: {e}")
        
        # Remove PIN column from class table
        try:
            conn.execute(text("ALTER TABLE class DROP COLUMN pin_code"))
            print("✅ Removed pin_code column from class table")
        except Exception as e:
            print(f"⚠️  pin_code column might not exist in class table: {e}")
        
        conn.commit()
    
    print("🎉 Student PIN migration completed!")

if __name__ == "__main__":
    migrate_student_pin()
