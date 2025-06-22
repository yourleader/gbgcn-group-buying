#!/usr/bin/env python3
"""
🧪 GBGCN Test Data Generator
Genera datos de prueba completos para probar el modelo GBGCN con:
- Usuarios diversos con perfiles realistas
- Items organizados por categorías
- Grupos de compra activos
- Interacciones usuario-item
- Conexiones sociales
- Datos para entrenar/probar recomendaciones
"""

import asyncio
import asyncpg
import random
import json
from datetime import datetime, timedelta
from faker import Faker
import uuid

# Configuración de base de datos
DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "user": "groupbuy", 
    "password": "password",
    "database": "groupbuy_db"
}

fake = Faker(['es_ES', 'en_US'])

class GBGCNDataGenerator:
    def __init__(self):
        self.conn = None
        self.users = []
        self.categories = []
        self.items = []
        self.groups = []
        
    async def connect(self):
        """Conectar a la base de datos"""
        try:
            self.conn = await asyncpg.connect(**DB_CONFIG)
            print("✅ Conectado a PostgreSQL")
        except Exception as e:
            print(f"❌ Error conectando a DB: {e}")
            raise
    
    async def create_categories(self):
        """Crear categorías de productos"""
        print("📂 Creando categorías...")
        
        categories_data = [
            ("tech", "Tecnología", "Dispositivos electrónicos y gadgets"),
            ("fashion", "Moda", "Ropa, calzado y accesorios"),
            ("home", "Hogar", "Artículos para el hogar y decoración"),
            ("sports", "Deportes", "Equipamiento deportivo y fitness"),
            ("beauty", "Belleza", "Cosméticos y productos de cuidado personal")
        ]
        
        for cat_id, name, description in categories_data:
            await self.conn.execute("""
                INSERT INTO categories (id, name, description, is_active, created_at, updated_at)
                VALUES ($1, $2, $3, true, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                updated_at = NOW()
            """, cat_id, name, description)
            
            self.categories.append({
                'id': cat_id,
                'name': name,
                'description': description
            })
        
        print(f"   ✅ {len(categories_data)} categorías creadas")
    
    async def create_users(self, count=15):
        """Crear usuarios diversos"""
        print(f"👥 Creando {count} usuarios...")
        
        # Mantener usuario de prueba existente
        existing_users = await self.conn.fetch("SELECT id, email FROM users")
        for user in existing_users:
            self.users.append({
                'id': user['id'],
                'email': user['email']
            })
        
        for i in range(count):
            user_id = str(uuid.uuid4())
            first_name = fake.first_name()
            last_name = fake.last_name()
            email = f"{first_name.lower()}.{last_name.lower()}{i}@example.com"
            username = f"{first_name.lower()}{last_name.lower()}{i}"
            
            # Generar métricas realistas
            reputation = round(random.uniform(0.0, 5.0), 2)
            groups_created = random.randint(0, 5)
            groups_joined = random.randint(1, 15)
            success_rate = round(random.uniform(0.3, 0.95), 2)
            
            await self.conn.execute("""
                INSERT INTO users (
                    id, email, username, password_hash, first_name, last_name,
                    phone, is_verified, is_active, role, reputation_score,
                    total_groups_created, total_groups_joined, success_rate,
                    created_at, updated_at
                ) VALUES (
                    $1, $2, $3, '$2b$12$dummy.hash.for.testing', $4, $5,
                    $6, $7, true, 'USER', $8, $9, $10, $11, NOW(), NOW()
                )
            """, 
            user_id, email, username, first_name, last_name,
            fake.phone_number()[:20], random.choice([True, False]),
            reputation, groups_created, groups_joined, success_rate)
            
            self.users.append({
                'id': user_id,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'reputation': reputation
            })
        
        print(f"   ✅ {len(self.users)} usuarios totales (incluyendo existentes)")
    
    async def create_items(self, count=20):
        """Crear items diversos por categoría"""
        print(f"📦 Creando {count} items adicionales...")
        
        items_data = [
            ("tech", "MacBook Pro M3", "Laptop profesional Apple", 2199.99, "Apple"),
            ("tech", "iPhone 15 Pro Max", "Smartphone premium", 1299.99, "Apple"),
            ("tech", "Samsung Galaxy S24", "Android flagship", 1199.99, "Samsung"),
            ("tech", "AirPods Pro 2", "Auriculares inalámbricos", 279.99, "Apple"),
            ("tech", "PlayStation 5", "Consola de videojuegos", 499.99, "Sony"),
            ("fashion", "Nike Air Jordan 1", "Zapatillas clásicas", 180.99, "Nike"),
            ("fashion", "Levi's 501 Jeans", "Jeans clásicos", 89.99, "Levi's"),
            ("fashion", "Ray-Ban Aviator", "Gafas de sol clásicas", 159.99, "Ray-Ban"),
            ("home", "Dyson V15 Detect", "Aspiradora inalámbrica", 649.99, "Dyson"),
            ("home", "Ninja Foodi", "Olla de presión multiuso", 199.99, "Ninja"),
            ("sports", "Peloton Bike+", "Bicicleta estática premium", 2495.99, "Peloton"),
            ("sports", "Bowflex SelectTech", "Mancuernas ajustables", 429.99, "Bowflex"),
            ("beauty", "Dyson Airwrap", "Estilizador de cabello", 569.99, "Dyson"),
            ("beauty", "Fenty Beauty Kit", "Kit de maquillaje", 89.99, "Fenty Beauty")
        ]
        
        for category_id, name, description, price, brand in items_data:
            item_id = str(uuid.uuid4())
            
            # Parámetros de grupo buying realistas
            min_group = random.randint(2, 5)
            max_group = random.randint(10, 50)
            
            # Specs realistas
            specs = {
                "color": random.choice(["Negro", "Blanco", "Gris", "Azul", "Rojo"]),
                "warranty": f"{random.randint(1, 3)} años",
                "shipping": "Envío gratuito",
                "discount_available": f"{random.randint(5, 25)}% off en grupo"
            }
            
            await self.conn.execute("""
                INSERT INTO items (
                    id, name, description, base_price, category_id, brand, model,
                    min_group_size, max_group_size, images, specifications,
                    is_active, is_group_buyable, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, true, true, NOW(), NOW()
                )
            """, 
            item_id, name, description, price, category_id, brand, name,
            min_group, max_group, ["https://example.com/image.jpg"], json.dumps(specs))
            
            self.items.append({
                'id': item_id,
                'name': name,
                'price': price,
                'category_id': category_id,
                'brand': brand,
                'min_group_size': min_group,
                'max_group_size': max_group
            })
        
        print(f"   ✅ {len(self.items)} items creados")
    
    async def create_groups(self, count=10):
        """Crear grupos de compra activos"""
        print(f"👨‍👩‍👧‍👦 Creando {count} grupos...")
        
        statuses = ['FORMING', 'OPEN', 'ACTIVE']
        
        for i in range(count):
            if not self.users or not self.items:
                continue
                
            group_id = str(uuid.uuid4())
            creator = random.choice(self.users)
            item = random.choice(self.items)
            
            target_quantity = random.randint(item['min_group_size'], min(item['max_group_size'], 20))
            current_quantity = random.randint(1, target_quantity)
            status = random.choice(statuses)
            
            # Precios realistas para group buying
            original_price = item['price']
            discount = random.uniform(0.1, 0.3)  # 10-30% descuento
            current_price_per_unit = original_price * (1 - discount * (current_quantity / target_quantity))
            
            end_date = datetime.now() + timedelta(days=random.randint(1, 30))
            estimated_delivery = end_date + timedelta(days=random.randint(3, 14))
            
            # Cálculos de probabilidad para GBGCN
            success_probability = round(random.uniform(0.3, 0.9), 3)
            social_influence = round(random.uniform(0.1, 0.8), 3)
            
            await self.conn.execute("""
                INSERT INTO groups (
                    id, title, description, target_quantity, current_quantity,
                    min_participants, status, end_date, delivery_address,
                    estimated_delivery_date, current_price_per_unit, total_amount,
                    creator_id, item_id, success_probability, social_influence_score,
                    created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, NOW(), NOW()
                )
            """,
            group_id, f"Grupo para {item['name']}", 
            f"Compremos {item['name']} juntos y ahorremos dinero",
            target_quantity, current_quantity, item['min_group_size'],
            status, end_date, fake.address()[:100],
            estimated_delivery, current_price_per_unit, current_price_per_unit * current_quantity,
            creator['id'], item['id'], success_probability, social_influence)
            
            self.groups.append({
                'id': group_id,
                'item_id': item['id'],
                'creator_id': creator['id'],
                'target_quantity': target_quantity,
                'current_quantity': current_quantity,
                'status': status,
                'success_probability': success_probability
            })
        
        print(f"   ✅ {count} grupos creados")
    
    async def create_social_connections(self):
        """Crear conexiones sociales entre usuarios"""
        print("🤝 Creando conexiones sociales...")
        
        connection_count = 0
        for user in self.users:
            # Cada usuario tiene entre 2-6 amigos
            num_friends = min(random.randint(2, 6), len(self.users) - 1)
            potential_friends = [u for u in self.users if u['id'] != user['id']]
            
            if len(potential_friends) >= num_friends:
                friends = random.sample(potential_friends, num_friends)
                
                for friend in friends:
                    connection_strength = round(random.uniform(0.3, 1.0), 2)
                    connection_type = random.choice(['friend', 'family', 'colleague'])
                    
                    await self.conn.execute("""
                        INSERT INTO social_connections (
                            id, user_id, friend_id, connection_strength,
                            interaction_frequency, connection_type, is_mutual,
                            created_at, last_interaction
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, true, NOW(), NOW()
                        ) ON CONFLICT DO NOTHING
                    """, 
                    str(uuid.uuid4()), user['id'], friend['id'],
                    connection_strength, round(random.uniform(0.1, 0.9), 2),
                    connection_type)
                    connection_count += 1
        
        print(f"   ✅ {connection_count} conexiones sociales creadas")
    
    async def create_user_interactions(self):
        """Crear interacciones usuario-item realistas"""
        print("🔄 Creando interacciones usuario-item...")
        
        interaction_types = ['VIEW', 'CLICK', 'SHARE', 'JOIN_GROUP', 'RATE']
        interaction_count = 0
        
        for user in self.users:
            # Cada usuario interactúa con 3-8 items
            num_interactions = min(random.randint(3, 8), len(self.items))
            selected_items = random.sample(self.items, num_interactions)
            
            for item in selected_items:
                # 1-3 interacciones por item
                for _ in range(random.randint(1, 3)):
                    interaction_type = random.choice(interaction_types)
                    interaction_value = round(random.uniform(0.1, 1.0), 2)
                    
                    await self.conn.execute("""
                        INSERT INTO user_item_interactions (
                            id, user_id, item_id, interaction_type,
                            interaction_value, created_at
                        ) VALUES (
                            $1, $2, $3, $4, $5, NOW() - INTERVAL '%s days'
                        )
                    """ % random.randint(0, 30),
                    str(uuid.uuid4()), user['id'], item['id'],
                    interaction_type, interaction_value)
                    interaction_count += 1
        
        print(f"   ✅ {interaction_count} interacciones creadas")
    
    async def create_recommendations(self):
        """Crear recomendaciones de ejemplo"""
        print("🎯 Creando recomendaciones GBGCN...")
        
        recommendation_count = 0
        for user in self.users:
            # 2-4 recomendaciones por usuario
            num_recommendations = min(random.randint(2, 4), len(self.items))
            recommended_items = random.sample(self.items, num_recommendations)
            
            for item in recommended_items:
                recommendation_score = round(random.uniform(0.5, 0.99), 3)
                success_probability = round(random.uniform(0.3, 0.9), 3)
                social_influence = round(random.uniform(0.1, 0.8), 3)
                
                recommendation_type = random.choice(['initiate', 'join'])
                target_group_size = random.randint(item['min_group_size'], item['max_group_size'])
                predicted_price = item['price'] * random.uniform(0.7, 0.9)
                
                await self.conn.execute("""
                    INSERT INTO group_recommendations (
                        id, user_id, item_id, recommendation_score,
                        success_probability, social_influence_score,
                        recommendation_type, target_group_size, predicted_price,
                        model_version, created_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, 'gbgcn_v1.0', NOW()
                    )
                """,
                str(uuid.uuid4()), user['id'], item['id'], recommendation_score,
                success_probability, social_influence, recommendation_type,
                target_group_size, predicted_price)
                recommendation_count += 1
        
        print(f"   ✅ {recommendation_count} recomendaciones creadas")
    
    async def print_summary(self):
        """Mostrar resumen de datos creados"""
        print("\n" + "="*60)
        print("📊 RESUMEN DE DATOS DE PRUEBA GBGCN")
        print("="*60)
        
        # Contar datos finales
        counts = await self.conn.fetchrow("""
            SELECT 
                (SELECT COUNT(*) FROM users) as usuarios,
                (SELECT COUNT(*) FROM categories) as categorias,
                (SELECT COUNT(*) FROM items WHERE is_active = true) as items,
                (SELECT COUNT(*) FROM groups) as grupos,
                (SELECT COUNT(*) FROM social_connections) as conexiones_sociales,
                (SELECT COUNT(*) FROM user_item_interactions) as interacciones,
                (SELECT COUNT(*) FROM group_recommendations) as recomendaciones
        """)
        
        print(f"👥 Usuarios: {counts['usuarios']}")
        print(f"📂 Categorías: {counts['categorias']}")
        print(f"📦 Items activos: {counts['items']}")
        print(f"👨‍👩‍👧‍👦 Grupos: {counts['grupos']}")
        print(f"🤝 Conexiones sociales: {counts['conexiones_sociales']}")
        print(f"🔄 Interacciones: {counts['interacciones']}")
        print(f"🎯 Recomendaciones: {counts['recomendaciones']}")
        
        print("\n✅ DATOS DE PRUEBA LISTOS PARA GBGCN")
        print("🔗 Ahora puedes probar:")
        print("   - GET /api/v1/recommendations/")
        print("   - GET /api/v1/groups/")
        print("   - GET /api/v1/social/connections")
        print("   - GET /api/v1/analytics/dashboard")
        
    async def close(self):
        """Cerrar conexión"""
        if self.conn:
            await self.conn.close()

async def main():
    """Función principal"""
    print("🚀 GBGCN Test Data Generator")
    print("🎯 Generando datos completos para probar el modelo GBGCN...")
    print()
    
    generator = GBGCNDataGenerator()
    
    try:
        await generator.connect()
        
        # Generar datos paso a paso
        await generator.create_categories()
        await generator.create_users(15)  # 15 usuarios nuevos
        await generator.create_items(14)  # 14 items nuevos
        await generator.create_groups(10)  # 10 grupos
        await generator.create_social_connections()
        await generator.create_user_interactions()
        await generator.create_recommendations()
        
        await generator.print_summary()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await generator.close()

if __name__ == "__main__":
    asyncio.run(main()) 