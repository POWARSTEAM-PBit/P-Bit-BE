#!/usr/bin/env python3
"""
Database migration script to set up proper table structure
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from db.init_engine import engine, Base
from db import db_models

def migrate_database():
    """Migrate database to new structure"""
    print("🔄 Starting database migration...")
    
    with engine.connect() as conn:
        # Drop existing tables in correct order (respecting foreign keys)
        print("🗑️  Dropping existing tables...")
        
        # Drop tables that might have foreign key constraints first
        tables_to_drop = ['class_member', 'class', 'tag']
        
        for table in tables_to_drop:
            try:
                conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
                print(f"✅ Dropped table: {table}")
            except Exception as e:
                print(f"⚠️  Could not drop {table}: {e}")
        
        # Keep user table as it has existing data
        print("✅ Keeping user table (preserving existing user data)")
        
        conn.commit()
    
    # Create new tables with proper structure
    print("🏗️  Creating new tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully!")
        
        # Verify tables were created
        with engine.connect() as conn:
            result = conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result.fetchall()]
            print(f"📋 Available tables: {tables}")
            
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise e

if __name__ == "__main__":
    migrate_database()
