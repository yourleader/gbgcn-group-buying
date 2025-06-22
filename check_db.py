#!/usr/bin/env python3
"""
Script para verificar datos en la base de datos
"""
import asyncio
import asyncpg

async def check_database():
    """Verificar qué datos existen en la DB"""
    print("🔍 VERIFICANDO DATOS EN BASE DE DATOS")
    print("=" * 50)
    
    try:
        conn = await asyncpg.connect(
            user="postgres",
            password="postgres", 
            database="groupbuy_db",
            host="localhost"
        )
        
        # Verificar items
        print("📦 ITEMS EN BASE DE DATOS:")
        items = await conn.fetch("SELECT id, name, base_price, is_active, category_id FROM items LIMIT 10")
        if items:
            for item in items:
                print(f"   • {item['name']} | ${item['base_price']} | Active: {item['is_active']} | Cat: {item['category_id'][:8] if item['category_id'] else 'None'}...")
        else:
            print("   ❌ No se encontraron items")
        
        # Verificar usuarios
        print(f"\n👥 USUARIOS EN BASE DE DATOS:")
        users = await conn.fetch("SELECT id, username, email, is_active FROM users LIMIT 5")
        if users:
            for user in users:
                print(f"   • {user['username']} ({user['email']}) | Active: {user['is_active']}")
        else:
            print("   ❌ No se encontraron usuarios")
        
        # Verificar categorías
        print(f"\n📂 CATEGORÍAS EN BASE DE DATOS:")
        categories = await conn.fetch("SELECT id, name, description FROM categories LIMIT 5")
        if categories:
            for cat in categories:
                print(f"   • {cat['name']} | {cat['description']}")
        else:
            print("   ❌ No se encontraron categorías")
        
        # Verificar tabla structure
        print(f"\n🏗️ ESTRUCTURA DE TABLA ITEMS:")
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'items' 
            ORDER BY ordinal_position
        """)
        for col in columns:
            print(f"   • {col['column_name']}: {col['data_type']} | Nullable: {col['is_nullable']}")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error conectando a DB: {e}")

if __name__ == "__main__":
    asyncio.run(check_database()) 