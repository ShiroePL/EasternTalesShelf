"""
Migration script to add OAuth authentication fields to the users table.
"""

import os
import sys
from sqlalchemy import create_engine, text
from app.config import DATABASE_URI

def migrate_users_table():
    """Add OAuth columns to users table"""
    print("Migrating users table to support OAuth authentication...")
    
    # Connect to database
    engine = create_engine(DATABASE_URI)
    print("DATABASE_URI: ", DATABASE_URI)
    conn = engine.connect()
    
    try:
        # Check if columns already exist to avoid errors
        columns_to_add = {
            'anilist_id': 'INTEGER UNIQUE',
            'display_name': 'VARCHAR(255)',
            'avatar_url': 'VARCHAR(255)',
            'access_token': 'VARCHAR(255)',
            'oauth_provider': 'VARCHAR(50)'
        }
        
        # Get existing columns using MariaDB compatible syntax
        existing_columns = []
        result = conn.execute(text("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'users'"))
        for row in result:
            existing_columns.append(row[0])  # Column name is at index 0 in MariaDB
        
        # Drop the NOT NULL constraint from password_hash if it exists
        if 'password_hash' in existing_columns:
            print("Modifying password_hash to allow NULL values...")
            
            # Create a new temporary table
            conn.execute(text("""
                CREATE TABLE users_temp (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    username VARCHAR(255) NOT NULL UNIQUE,
                    password_hash VARCHAR(255)
                )
            """))
            
            # Copy data to the temporary table
            conn.execute(text("""
                INSERT INTO users_temp (id, username, password_hash)
                SELECT id, username, password_hash FROM users
            """))
            
            # Drop the old table
            conn.execute(text("DROP TABLE users"))
            
            # Rename the temporary table to the original table name
            conn.execute(text("RENAME TABLE users_temp TO users"))
            
            print("Password_hash column modified successfully.")
        
        # Add the new columns
        for column_name, column_type in columns_to_add.items():
            if column_name not in existing_columns:
                print(f"Adding column {column_name}...")
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"))
        
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        return False
    finally:
        conn.close()
    
    return True

if __name__ == "__main__":
    migrate_users_table() 