#!/usr/bin/env python3
"""
Script to create PostgreSQL database for Group Buying GBGCN system
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def create_database():
    """Create the groupbuy_db database"""
    
    print("🔗 Connecting to PostgreSQL...")
    
    # Connect to PostgreSQL (default database)
    try:
        connection = psycopg2.connect(
            host="localhost",
            port="5432",
            user="postgres",
            password="password"  # Change this to your PostgreSQL password
        )
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = connection.cursor()
        
        print("✅ Connected to PostgreSQL!")
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'groupbuy_db'")
        exists = cursor.fetchone()
        
        if exists:
            print("📊 Database 'groupbuy_db' already exists")
        else:
            # Create database
            cursor.execute("CREATE DATABASE groupbuy_db")
            print("✅ Created database 'groupbuy_db'")
        
        # Create user if not exists
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = 'groupbuy'")
        user_exists = cursor.fetchone()
        
        if not user_exists:
            cursor.execute("CREATE USER groupbuy WITH PASSWORD 'password'")
            cursor.execute("GRANT ALL PRIVILEGES ON DATABASE groupbuy_db TO groupbuy")
            print("✅ Created user 'groupbuy' with privileges")
        else:
            print("👤 User 'groupbuy' already exists")
        
        cursor.close()
        connection.close()
        
        print("🎯 Database setup completed successfully!")
        print("📝 Connection string: postgresql://groupbuy:password@localhost:5432/groupbuy_db")
        
    except psycopg2.Error as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure PostgreSQL is running and check your credentials")
        print("💡 Default connection: host=localhost, user=postgres, password=password")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Group Buying GBGCN - Database Setup")
    print("=" * 50)
    
    success = create_database()
    
    if success:
        print("\n🎉 Ready to run the API!")
        print("Next step: python -m uvicorn src.api.main:app --reload")
    else:
        print("\n🔧 Please check your PostgreSQL configuration") 