#!/usr/bin/env python3
"""
Script para generar datos de ejemplo para entrenar el modelo GBGCN
"""
import asyncio
import sys
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Agregar src al path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from database.models import (
    User, Item, Category, Group, GroupMember, 
    SocialConnection, UserItemInteraction, PriceTier
)
import json

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/groupbuy_db"

async def generate_sample_data():
    """Generar datos de ejemplo para el sistema GBGCN"""
    print("🔧 Generando datos de ejemplo para GBGCN...")
    print("=" * 50)
    
    # Crear engine y session
    engine = create_async_engine(DATABASE_URL)
    async_session = async_sessionmaker(engine, class_=AsyncSession)
    
    async with async_session() as session:
        try:
            # 1. Crear categorías
            print("📂 Creando categorías...")
            categories = [
                Category(id=str(uuid.uuid4()), name="Electronics", description="Electronic devices and gadgets"),
                Category(id=str(uuid.uuid4()), name="Clothing", description="Fashion and apparel"),
                Category(id=str(uuid.uuid4()), name="Home & Garden", description="Home improvement and garden supplies"),
                Category(id=str(uuid.uuid4()), name="Sports", description="Sports equipment and accessories"),
                Category(id=str(uuid.uuid4()), name="Books", description="Books and educational materials")
            ]
            
            for category in categories:
                session.add(category)
            await session.commit()
            print(f"   ✅ {len(categories)} categorías creadas")
            
            # 2. Crear usuarios de ejemplo
            print("👥 Creando usuarios de ejemplo...")
            users = []
            for i in range(50):  # 50 usuarios
                user = User(
                    id=str(uuid.uuid4()),
                    username=f"user_{i:03d}",
                    email=f"user{i:03d}@example.com",
                    password_hash="$2b$12$dummy_hash_for_testing",  # Hash dummy
                    first_name=f"User{i}",
                    last_name=f"Test{i}",
                    phone=f"+123456{i:04d}",
                    is_verified=True,
                    is_active=True,
                    role="user",
                    reputation_score=random.uniform(0.1, 5.0),
                    total_groups_created=random.randint(0, 10),
                    total_groups_joined=random.randint(0, 20),
                    success_rate=random.uniform(0.3, 0.95),
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 365))
                )
                users.append(user)
                session.add(user)
            
            await session.commit()
            print(f"   ✅ {len(users)} usuarios creados")
            
            # 3. Crear items de ejemplo
            print("🛍️ Creando items de ejemplo...")
            items_data = [
                # Electronics
                {"name": "iPhone 15 Pro", "base_price": 999.99, "category": 0, "min_size": 5, "max_size": 50},
                {"name": "Samsung Galaxy S24", "base_price": 899.99, "category": 0, "min_size": 5, "max_size": 40},
                {"name": "MacBook Air M3", "base_price": 1299.99, "category": 0, "min_size": 3, "max_size": 20},
                {"name": "AirPods Pro", "base_price": 249.99, "category": 0, "min_size": 10, "max_size": 100},
                {"name": "iPad Pro", "base_price": 799.99, "category": 0, "min_size": 5, "max_size": 30},
                
                # Clothing
                {"name": "Nike Air Jordan 1", "base_price": 179.99, "category": 1, "min_size": 10, "max_size": 50},
                {"name": "Levi's 501 Jeans", "base_price": 89.99, "category": 1, "min_size": 15, "max_size": 60},
                {"name": "Adidas Hoodie", "base_price": 69.99, "category": 1, "min_size": 20, "max_size": 80},
                
                # Home & Garden
                {"name": "Dyson V15 Vacuum", "base_price": 549.99, "category": 2, "min_size": 5, "max_size": 25},
                {"name": "KitchenAid Mixer", "base_price": 379.99, "category": 2, "min_size": 8, "max_size": 30},
                
                # Sports
                {"name": "Yoga Mat Premium", "base_price": 79.99, "category": 3, "min_size": 20, "max_size": 100},
                {"name": "Running Shoes", "base_price": 149.99, "category": 3, "min_size": 15, "max_size": 60},
                
                # Books
                {"name": "Programming Books Bundle", "base_price": 199.99, "category": 4, "min_size": 10, "max_size": 50},
                {"name": "Design Thinking Kit", "base_price": 89.99, "category": 4, "min_size": 15, "max_size": 40}
            ]
            
            items = []
            for i, item_data in enumerate(items_data):
                item = Item(
                    id=str(uuid.uuid4()),
                    name=item_data["name"],
                    description=f"High-quality {item_data['name']} with great group buying discount opportunities",
                    base_price=item_data["base_price"],
                    category_id=categories[item_data["category"]].id,
                    min_group_size=item_data["min_size"],
                    max_group_size=item_data["max_size"],
                    images=[f"https://example.com/images/item_{i}_1.jpg", f"https://example.com/images/item_{i}_2.jpg"],
                    specifications={"color": "Multiple", "warranty": "1 year", "shipping": "Free"},
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 180))
                )
                items.append(item)
                session.add(item)
            
            # Crear price tiers para cada item
            for item in items:
                for j in range(3):  # 3 tiers por item
                    tier = PriceTier(
                        id=str(uuid.uuid4()),
                        item_id=item.id,
                        min_quantity=j * 10 + item.min_group_size,
                        max_quantity=(j + 1) * 15 + item.min_group_size if j < 2 else None,
                        discount_percentage=0.05 + (j * 0.1),  # 5%, 15%, 25%
                        final_price=item.base_price * (1 - (0.05 + (j * 0.1)))
                    )
                    session.add(tier)
            
            await session.commit()
            print(f"   ✅ {len(items)} items creados con price tiers")
            
            # 4. Crear conexiones sociales
            print("🌐 Creando red social...")
            social_connections = []
            for i in range(200):  # 200 conexiones sociales
                user1 = random.choice(users)
                user2 = random.choice(users)
                
                if user1.id != user2.id:
                    connection = SocialConnection(
                        id=str(uuid.uuid4()),
                        user_id=user1.id,
                        friend_id=user2.id,
                        connection_strength=random.uniform(0.1, 1.0),
                        interaction_frequency=random.uniform(0.1, 0.9),
                        connection_type=random.choice(["friend", "colleague", "family", "acquaintance"]),
                        is_mutual=random.choice([True, False]),
                        created_at=datetime.utcnow() - timedelta(days=random.randint(1, 300)),
                        last_interaction=datetime.utcnow() - timedelta(days=random.randint(1, 30))
                    )
                    social_connections.append(connection)
                    session.add(connection)
            
            await session.commit()
            print(f"   ✅ {len(social_connections)} conexiones sociales creadas")
            
            # 5. Crear grupos de compra
            print("👥 Creando grupos de compra...")
            groups = []
            for i in range(30):  # 30 grupos
                item = random.choice(items)
                creator = random.choice(users)
                
                group = Group(
                    id=str(uuid.uuid4()),
                    title=f"Group Buy: {item.name} #{i+1}",
                    description=f"Let's buy {item.name} together for better prices!",
                    item_id=item.id,
                    target_quantity=random.randint(item.min_group_size, min(item.max_group_size, 50)),
                    current_quantity=0,
                    min_participants=item.min_group_size,
                    status=random.choice(["active", "forming", "completed", "cancelled"]),
                    end_date=datetime.utcnow() + timedelta(days=random.randint(7, 30)),
                    delivery_address=f"{random.randint(100, 999)} Main St, City {i}",
                    current_price_per_unit=item.base_price * random.uniform(0.8, 0.95),
                    creator_id=creator.id,
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 60)),
                    success_probability=random.uniform(0.2, 0.9),
                    social_influence_score=random.uniform(0.1, 0.8)
                )
                groups.append(group)
                session.add(group)
            
            await session.commit()
            print(f"   ✅ {len(groups)} grupos creados")
            
            # 6. Crear membresías de grupos
            print("🔗 Creando membresías de grupos...")
            group_members = []
            for group in groups:
                # Agregar el creador
                creator_member = GroupMember(
                    id=str(uuid.uuid4()),
                    user_id=group.creator_id,
                    group_id=group.id,
                    quantity=random.randint(1, 3),
                    status="confirmed",
                    is_initiator=True,
                    social_influence_received=0.0,
                    influence_from_friends=0,
                    joined_at=group.created_at,
                    confirmed_at=group.created_at
                )
                group_members.append(creator_member)
                session.add(creator_member)
                
                # Agregar otros miembros
                num_members = random.randint(0, min(15, group.target_quantity - 1))
                potential_members = [u for u in users if u.id != group.creator_id]
                selected_members = random.sample(potential_members, min(num_members, len(potential_members)))
                
                for member_user in selected_members:
                    member = GroupMember(
                        id=str(uuid.uuid4()),
                        user_id=member_user.id,
                        group_id=group.id,
                        quantity=random.randint(1, 2),
                        status=random.choice(["confirmed", "pending", "declined"]),
                        is_initiator=False,
                        social_influence_received=random.uniform(0.0, 0.8),
                        influence_from_friends=random.randint(0, 5),
                        joined_at=group.created_at + timedelta(days=random.randint(1, 7)),
                        confirmed_at=group.created_at + timedelta(days=random.randint(1, 10)) if random.random() > 0.3 else None
                    )
                    group_members.append(member)
                    session.add(member)
                
                # Actualizar current_quantity del grupo
                confirmed_quantity = sum(m.quantity for m in group_members if m.group_id == group.id and m.status == "confirmed")
                group.current_quantity = confirmed_quantity
                group.total_amount = confirmed_quantity * group.current_price_per_unit
            
            await session.commit()
            print(f"   ✅ {len(group_members)} membresías creadas")
            
            # 7. Crear interacciones usuario-item
            print("📊 Creando interacciones usuario-item...")
            interactions = []
            for i in range(1000):  # 1000 interacciones
                user = random.choice(users)
                item = random.choice(items)
                
                interaction = UserItemInteraction(
                    id=str(uuid.uuid4()),
                    user_id=user.id,
                    item_id=item.id,
                    interaction_type=random.choice(["view", "like", "share", "add_to_wishlist", "join_group"]),
                    interaction_value=random.uniform(0.1, 1.0),
                    group_id=random.choice(groups).id if random.random() > 0.5 else None,
                    session_id=f"session_{random.randint(1000, 9999)}",
                    device_type=random.choice(["mobile", "desktop", "tablet"]),
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 90))
                )
                interactions.append(interaction)
                session.add(interaction)
            
            await session.commit()
            print(f"   ✅ {len(interactions)} interacciones creadas")
            
            print("\n🎉 ¡Datos de ejemplo generados exitosamente!")
            print(f"📊 Resumen:")
            print(f"   👥 {len(users)} usuarios")
            print(f"   🛍️ {len(items)} items")
            print(f"   📂 {len(categories)} categorías")
            print(f"   👥 {len(groups)} grupos")
            print(f"   🔗 {len(group_members)} membresías")
            print(f"   🌐 {len(social_connections)} conexiones sociales")
            print(f"   📊 {len(interactions)} interacciones")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            await session.rollback()
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(generate_sample_data()) 