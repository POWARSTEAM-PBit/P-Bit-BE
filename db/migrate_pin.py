#!/usr/bin/env python3
"""
Migration script to add PIN column to existing classes
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from db.init_engine import engine
from db import db_models

def migrate_pin_column():
    """Add PIN column to existing classes"""
    print("🔄 Adding PIN column to existing classes...")
    
    with engine.connect() as conn:
        # Add PIN column if it doesn't exist
        try:
            conn.execute(text("ALTER TABLE class ADD COLUMN pin_code VARCHAR(4) NOT NULL DEFAULT '0000'"))
            print("✅ Added PIN column to class table")
        except Exception as e:
            print(f"⚠️  PIN column might already exist: {e}")
        
        # Update existing classes with random PINs
        try:
            # Get all classes without PINs
            result = conn.execute(text("SELECT id FROM class WHERE pin_code = '0000'"))
            classes = result.fetchall()
            
            if classes:
                print(f"🔄 Updating {len(classes)} existing classes with PIN codes...")
                
                for class_row in classes:
                    class_id = class_row[0]
                    new_pin = db_models.generate_pin_code()
                    
                    conn.execute(
                        text("UPDATE class SET pin_code = :pin WHERE id = :class_id"),
                        {"pin": new_pin, "class_id": class_id}
                    )
                    print(f"✅ Updated class {class_id} with PIN: {new_pin}")
                
                conn.commit()
                print("✅ All existing classes updated with PIN codes")
            else:
                print("✅ No existing classes need PIN updates")
                
        except Exception as e:
            print(f"❌ Error updating PIN codes: {e}")
            conn.rollback()
    
    print("🎉 PIN migration completed!")

if __name__ == "__main__":
    migrate_pin_column()
