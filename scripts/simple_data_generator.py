#!/usr/bin/env python3
"""
Script simple para generar datos de ejemplo para GBGCN
"""
import sys
import os
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Agregar src al path
sys.path.append(str(Path(__file__).parent.parent / "src"))

# Importaciones directas
import asyncio
import asyncpg
import json

async def generate_simple_data():
    """Generar datos de ejemplo usando asyncpg directamente"""
    print("🔧 Generando datos de ejemplo para GBGCN...")
    print("=" * 50)
    
    # Conectar directamente a PostgreSQL
    conn = await asyncpg.connect(
        user="postgres",
        password="postgres", 
        database="groupbuy_db",
        host="localhost",
        port=5432
    )
    
    try:
        # 1. Limpiar datos existentes (opcional)
        print("🧹 Limpiando datos anteriores...")
        await conn.execute("TRUNCATE TABLE user_item_interactions CASCADE")
        await conn.execute("TRUNCATE TABLE group_members CASCADE") 
        await conn.execute("TRUNCATE TABLE social_connections CASCADE")
        await conn.execute("TRUNCATE TABLE group_recommendations CASCADE")
        await conn.execute("TRUNCATE TABLE gbgcn_embeddings CASCADE")
        await conn.execute("TRUNCATE TABLE groups CASCADE")
        await conn.execute("TRUNCATE TABLE price_tiers CASCADE")
        await conn.execute("TRUNCATE TABLE items CASCADE")
        await conn.execute("TRUNCATE TABLE categories CASCADE")
        await conn.execute("TRUNCATE TABLE users CASCADE")
        
        # 2. Crear categorías
        print("📂 Creando categorías...")
        categories = [
            (str(uuid.uuid4()), "Electronics", "Electronic devices and gadgets"),
            (str(uuid.uuid4()), "Clothing", "Fashion and apparel"),
            (str(uuid.uuid4()), "Home & Garden", "Home improvement and garden supplies"),
            (str(uuid.uuid4()), "Sports", "Sports equipment and accessories"),
            (str(uuid.uuid4()), "Books", "Books and educational materials")
        ]
        
        for cat_id, name, desc in categories:
            await conn.execute(
                "INSERT INTO categories (id, name, description, created_at, updated_at) VALUES ($1, $2, $3, $4, $5)",
                cat_id, name, desc, datetime.utcnow(), datetime.utcnow()
            )
        print(f"   ✅ {len(categories)} categorías creadas")
        
        # 3. Crear usuarios
        print("👥 Creando usuarios...")
        users = []
        for i in range(20):  # 20 usuarios para empezar
            user_id = str(uuid.uuid4())
            users.append(user_id)
            
            await conn.execute("""
                INSERT INTO users (
                    id, username, email, password_hash, first_name, last_name,
                    phone, is_verified, is_active, role, reputation_score,
                    total_groups_created, total_groups_joined, success_rate,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
            """,
                user_id, f"user_{i:03d}", f"user{i:03d}@example.com",
                "$2b$12$dummy_hash_for_testing", f"User{i}", f"Test{i}",
                f"+123456{i:04d}", True, True, "user", random.uniform(0.1, 5.0),
                random.randint(0, 10), random.randint(0, 20), random.uniform(0.3, 0.95),
                datetime.utcnow(), datetime.utcnow()
            )
        print(f"   ✅ {len(users)} usuarios creados")
        
        # 4. Crear items
        print("🛍️ Creando items...")
        items_data = [
            ("iPhone 15 Pro", 999.99, 0, 5, 50),
            ("Samsung Galaxy S24", 899.99, 0, 5, 40),
            ("MacBook Air M3", 1299.99, 0, 3, 20),
            ("AirPods Pro", 249.99, 0, 10, 100),
            ("Nike Air Jordan 1", 179.99, 1, 10, 50),
            ("Levi's 501 Jeans", 89.99, 1, 15, 60),
            ("Dyson V15 Vacuum", 549.99, 2, 5, 25),
            ("Yoga Mat Premium", 79.99, 3, 20, 100),
            ("Programming Books Bundle", 199.99, 4, 10, 50)
        ]
        
        items = []
        for i, (name, price, cat_idx, min_size, max_size) in enumerate(items_data):
            item_id = str(uuid.uuid4())
            items.append(item_id)
            
            await conn.execute("""
                INSERT INTO items (
                    id, name, description, base_price, category_id,
                    min_group_size, max_group_size, images, specifications,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
                item_id, name, f"High-quality {name} with group buying discounts",
                price, categories[cat_idx][0], min_size, max_size,
                [f"https://example.com/images/item_{i}_1.jpg"],
                json.dumps({"color": "Multiple", "warranty": "1 year"}),
                datetime.utcnow(), datetime.utcnow()
            )
            
            # Crear price tiers para cada item
            for j in range(3):
                tier_id = str(uuid.uuid4())
                discount = 0.05 + (j * 0.1)  # 5%, 15%, 25%
                await conn.execute("""
                    INSERT INTO price_tiers (
                        id, item_id, min_quantity, max_quantity,
                        discount_percentage, final_price
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                """,
                    tier_id, item_id, j * 5 + min_size,
                    (j + 1) * 10 + min_size if j < 2 else None,
                    discount, price * (1 - discount)
                )
        
        print(f"   ✅ {len(items)} items creados con price tiers")
        
        # 5. Crear grupos
        print("👥 Creando grupos...")
        groups = []
        for i in range(10):  # 10 grupos
            group_id = str(uuid.uuid4())
            groups.append(group_id)
            
            item_id = random.choice(items)
            creator_id = random.choice(users)
            
            await conn.execute("""
                INSERT INTO groups (
                    id, title, description, item_id, target_quantity,
                    current_quantity, min_participants, status, end_date,
                    delivery_address, current_price_per_unit, creator_id,
                    created_at, updated_at, success_probability,
                    social_influence_score
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
            """,
                group_id, f"Group Buy #{i+1}", f"Group buying opportunity #{i+1}",
                item_id, random.randint(5, 30), random.randint(1, 15),
                random.randint(3, 8), "active",
                datetime.utcnow() + timedelta(days=random.randint(7, 30)),
                f"{random.randint(100, 999)} Main St, City {i}",
                random.uniform(50.0, 500.0), creator_id,
                datetime.utcnow(), datetime.utcnow(),
                random.uniform(0.2, 0.9), random.uniform(0.1, 0.8)
            )
        
        print(f"   ✅ {len(groups)} grupos creados")
        
        # 6. Crear interacciones
        print("📊 Creando interacciones...")
        for i in range(100):  # 100 interacciones
            interaction_id = str(uuid.uuid4())
            user_id = random.choice(users)
            item_id = random.choice(items)
            
            await conn.execute("""
                INSERT INTO user_item_interactions (
                    id, user_id, item_id, interaction_type,
                    interaction_value, session_id, device_type, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
                interaction_id, user_id, item_id,
                random.choice(["view", "like", "share", "add_to_wishlist"]),
                random.uniform(0.1, 1.0), f"session_{random.randint(1000, 9999)}",
                random.choice(["mobile", "desktop", "tablet"]),
                datetime.utcnow() - timedelta(days=random.randint(1, 30))
            )
        
        print("   ✅ 100 interacciones creadas")
        
        # 7. Crear conexiones sociales
        print("🌐 Creando red social...")
        created_connections = set()
        connections_count = 0
        for i in range(50):  # Intentar 50 veces para crear conexiones únicas
            user1 = random.choice(users)
            user2 = random.choice(users)
            
            # Evitar duplicados y auto-conexiones
            if user1 != user2 and (user1, user2) not in created_connections and (user2, user1) not in created_connections:
                connection_id = str(uuid.uuid4())
                await conn.execute("""
                    INSERT INTO social_connections (
                        id, user_id, friend_id, connection_strength,
                        interaction_frequency, connection_type, is_mutual,
                        created_at, last_interaction
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                    connection_id, user1, user2, random.uniform(0.1, 1.0),
                    random.uniform(0.1, 0.9), "friend", True,
                    datetime.utcnow() - timedelta(days=random.randint(1, 100)),
                    datetime.utcnow() - timedelta(days=random.randint(1, 10))
                )
                created_connections.add((user1, user2))
                connections_count += 1
        
        print(f"   ✅ {connections_count} conexiones sociales creadas")
        
        print("\n🎉 ¡Datos de ejemplo generados exitosamente!")
        print("📊 Resumen:")
        print(f"   👥 {len(users)} usuarios")
        print(f"   🛍️ {len(items)} items")
        print(f"   📂 {len(categories)} categorías")
        print(f"   👥 {len(groups)} grupos")
        print(f"   📊 100 interacciones")
        print(f"   🌐 {connections_count} conexiones sociales")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(generate_simple_data()) 