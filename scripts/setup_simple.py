#!/usr/bin/env python3
"""
Simple setup script for Group Buying GBGCN system
"""

import asyncio
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine
from src.core.config import settings
from src.database.models import Base

async def create_database_if_not_exists():
    """Create database if it doesn't exist"""
    try:
        print("🔗 Connecting to PostgreSQL...")
        
        # Extract connection parameters from URL
        db_url = settings.DATABASE_URL.replace("postgresql://", "")
        
        # For simplicity, use default connection
        conn = await asyncpg.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password="password"  # Change this to your actual password
        )
        
        # Check if database exists
        result = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = 'groupbuy_db'"
        )
        
        if not result:
            await conn.execute("CREATE DATABASE groupbuy_db")
            print("✅ Created database 'groupbuy_db'")
        else:
            print("📊 Database 'groupbuy_db' already exists")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database creation failed: {e}")
        print("💡 Make sure PostgreSQL is running")
        print("💡 You can also use SQLite by changing the DATABASE_URL")
        return False

async def create_tables():
    """Create all tables using SQLAlchemy"""
    try:
        print("📋 Creating database tables...")
        
        # Use async engine
        engine = create_async_engine(settings.DATABASE_URL)
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        await engine.dispose()
        print("✅ Database tables created successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Table creation failed: {e}")
        return False

async def main():
    """Main setup function"""
    print("🚀 Group Buying GBGCN - Simple Setup")
    print("=" * 50)
    
    # Create database
    db_success = await create_database_if_not_exists()
    
    if db_success:
        # Create tables
        tables_success = await create_tables()
        
        if tables_success:
            print("\n🎉 Setup completed successfully!")
            print("✅ Database ready")
            print("✅ Tables created")
            print("\n🚀 You can now run the API:")
            print("   python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000")
        else:
            print("\n❌ Table creation failed")
    else:
        print("\n❌ Database setup failed")
        print("\n💡 Alternative: Use SQLite")
        print("   Change DATABASE_URL in .env to: sqlite+aiosqlite:///./groupbuy.db")

if __name__ == "__main__":
    asyncio.run(main()) 