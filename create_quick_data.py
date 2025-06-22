#!/usr/bin/env python3
"""
Quick data creation for testing the GBGCN API
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

async def create_quick_test_data():
    from src.database.connection import get_db
    from sqlalchemy import text
    
    async for db in get_db():
        print("🔧 Creating quick test data...")
        
        try:
            # Create categories first (if they don't exist)
            await db.execute(text("""
                INSERT INTO categories (id, name, description, created_at, updated_at) VALUES 
                ('cat1', 'Electronics', 'Electronic devices', NOW(), NOW()),
                ('cat2', 'Clothing', 'Clothing and accessories', NOW(), NOW()),
                ('cat3', 'Home', 'Home and garden', NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
            """))
            
            # Create test items
            await db.execute(text("""
                INSERT INTO items (
                    id, name, description, base_price, category_id, brand, model,
                    min_group_size, max_group_size, images, specifications,
                    is_active, is_group_buyable, created_at, updated_at
                ) VALUES 
                ('item1', 'iPhone 15 Pro', 'Apple iPhone 15 Pro 128GB', 999.99, 'cat1', 'Apple', 'iPhone 15 Pro',
                 2, 50, '["https://example.com/iphone.jpg"]', '{"storage": "128GB", "color": "Natural Titanium"}', 
                 true, true, NOW(), NOW()),
                 
                ('item2', 'Samsung Galaxy S24', 'Samsung Galaxy S24 256GB', 899.99, 'cat1', 'Samsung', 'Galaxy S24',
                 2, 30, '["https://example.com/samsung.jpg"]', '{"storage": "256GB", "color": "Phantom Black"}', 
                 true, true, NOW(), NOW()),
                 
                ('item3', 'MacBook Air M3', 'Apple MacBook Air with M3 chip', 1299.99, 'cat1', 'Apple', 'MacBook Air M3',
                 3, 20, '["https://example.com/macbook.jpg"]', '{"memory": "16GB", "storage": "512GB"}', 
                 true, true, NOW(), NOW()),
                 
                ('item4', 'Nike Air Max', 'Nike Air Max 270 Sneakers', 150.00, 'cat2', 'Nike', 'Air Max 270',
                 5, 100, '["https://example.com/nike.jpg"]', '{"size": "US 10", "color": "White/Black"}', 
                 true, true, NOW(), NOW()),
                 
                ('item5', 'Sony WH-1000XM5', 'Wireless Noise Canceling Headphones', 399.99, 'cat1', 'Sony', 'WH-1000XM5',
                 2, 25, '["https://example.com/sony.jpg"]', '{"color": "Black", "battery": "30hrs"}', 
                 true, true, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
            """))
            
            await db.commit()
            
            # Verify creation
            result = await db.execute(text("SELECT COUNT(*) FROM items WHERE is_active = true"))
            active_count = result.scalar()
            
            result = await db.execute(text("SELECT name, base_price, brand FROM items WHERE is_active = true"))
            items = result.fetchall()
            
            print(f"✅ Created {active_count} active items:")
            for item in items:
                print(f"  - {item.name}: ${item.base_price} ({item.brand})")
                
            print("🎉 Test data creation completed!")
            
        except Exception as e:
            await db.rollback()
            print(f"❌ Error creating data: {e}")
            raise
        
        break

if __name__ == "__main__":
    asyncio.run(create_quick_test_data()) 