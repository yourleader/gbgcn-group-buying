#!/usr/bin/env python3
"""
🔧 Agregar Datos de Muestra para GBGCN
Este script crea usuarios, items, grupos e interacciones para probar el modelo completo
"""

import requests
import json
import time
import random

BASE_URL = "http://127.0.0.1:8000/api/v1"

class SampleDataCreator:
    def __init__(self):
        self.tokens = {}
        self.users = []
        self.items = []
        self.groups = []
        
    def print_banner(self):
        print("🔧 CREANDO DATOS DE MUESTRA PARA GBGCN")
        print("=" * 50)
        print("📊 Esto creará datos completos para probar el modelo")
        print("🤖 Incluye: Usuarios, Items, Grupos, Interacciones")
        print("=" * 50)
    
    def create_users(self):
        """Crear usuarios de muestra"""
        print("\n👥 Creando usuarios de muestra...")
        
        users_data = [
            {
                "username": "maria_garcia", "email": "maria@example.com", "password": "password123",
                "first_name": "María", "last_name": "García", "phone": "+34123456789"
            },
            {
                "username": "carlos_lopez", "email": "carlos@example.com", "password": "password123",
                "first_name": "Carlos", "last_name": "López", "phone": "+34123456790"
            },
            {
                "username": "ana_martinez", "email": "ana@example.com", "password": "password123",
                "first_name": "Ana", "last_name": "Martínez", "phone": "+34123456791"
            },
            {
                "username": "jose_rodriguez", "email": "jose@example.com", "password": "password123",
                "first_name": "José", "last_name": "Rodríguez", "phone": "+34123456792"
            },
            {
                "username": "laura_fernandez", "email": "laura@example.com", "password": "password123",
                "first_name": "Laura", "last_name": "Fernández", "phone": "+34123456793"
            }
        ]
        
        for user_data in users_data:
            try:
                response = requests.post(f"{BASE_URL}/register", json=user_data)
                if response.status_code == 201:
                    user = response.json()
                    self.users.append(user)
                    print(f"   ✅ {user_data['first_name']} {user_data['last_name']} creado")
                    
                    # Hacer login para obtener token
                    login_response = requests.post(f"{BASE_URL}/login", json={
                        "email": user_data["email"],
                        "password": user_data["password"]
                    })
                    if login_response.status_code == 200:
                        token = login_response.json()["access_token"]
                        self.tokens[user["id"]] = token
                        
                else:
                    print(f"   ⚠️ {user_data['first_name']} ya existe")
                    
            except Exception as e:
                print(f"   ❌ Error con {user_data['first_name']}: {e}")
        
        print(f"✅ {len(self.users)} usuarios creados con tokens")
    
    def create_items(self):
        """Crear items de muestra"""
        print("\n🛍️ Creando items de muestra...")
        
        items_data = [
            {
                "name": "iPhone 15 Pro", "description": "Último iPhone con características avanzadas",
                "base_price": 999.99, "category": "Electronics"
            },
            {
                "name": "MacBook Air M3", "description": "Portátil potente para trabajo y creatividad",
                "base_price": 1299.99, "category": "Electronics"
            },
            {
                "name": "AirPods Pro", "description": "Auriculares inalámbricos premium",
                "base_price": 249.99, "category": "Electronics"
            },
            {
                "name": "Nintendo Switch OLED", "description": "Consola de videojuegos híbrida",
                "base_price": 349.99, "category": "Gaming"
            },
            {
                "name": "Samsung 4K TV 55\"", "description": "Televisor 4K con tecnología QLED",
                "base_price": 799.99, "category": "Electronics"
            },
            {
                "name": "Sony PlayStation 5", "description": "Consola de videojuegos de nueva generación",
                "base_price": 499.99, "category": "Gaming"
            },
            {
                "name": "Dyson V15 Detect", "description": "Aspiradora inalámbrica con láser",
                "base_price": 649.99, "category": "Home"
            },
            {
                "name": "Robot Aspirador Roomba", "description": "Aspiradora robótica inteligente",
                "base_price": 399.99, "category": "Home"
            }
        ]
        
        if not self.tokens:
            print("❌ No hay tokens disponibles")
            return
        
        # Usar el primer token disponible
        token = list(self.tokens.values())[0]
        headers = {"Authorization": f"Bearer {token}"}
        
        for item_data in items_data:
            try:
                # Intentar diferentes endpoints para crear items
                endpoints_to_try = ["/items", "/items/create", "/api/v1/items"]
                
                item_created = False
                for endpoint in endpoints_to_try:
                    try:
                        response = requests.post(f"{BASE_URL.replace('/api/v1', '')}{endpoint}", 
                                               json=item_data, headers=headers)
                        if response.status_code in [200, 201]:
                            item = response.json()
                            self.items.append(item)
                            print(f"   ✅ {item_data['name']} creado")
                            item_created = True
                            break
                    except:
                        continue
                
                if not item_created:
                    print(f"   ⚠️ No se pudo crear {item_data['name']}")
                    
            except Exception as e:
                print(f"   ❌ Error con {item_data['name']}: {e}")
        
        print(f"✅ {len(self.items)} items creados")
    
    def create_groups(self):
        """Crear grupos de compra"""
        print("\n👥 Creando grupos de compra...")
        
        if not self.items or not self.tokens:
            print("❌ Necesitamos items y usuarios para crear grupos")
            return
        
        # Crear grupos para algunos items
        for i, item in enumerate(self.items[:4]):  # Solo los primeros 4 items
            try:
                # Usar diferentes usuarios como creadores
                user_id = list(self.tokens.keys())[i % len(self.tokens)]
                token = self.tokens[user_id]
                headers = {"Authorization": f"Bearer {token}"}
                
                group_data = {
                    "title": f"Grupo {item['name']} - Descuento Especial",
                    "description": f"Compremos juntos {item['name']} y ahorremos dinero",
                    "item_id": item["id"],
                    "target_quantity": random.randint(5, 15),
                    "current_quantity": 1,
                    "discount_percentage": round(random.uniform(0.1, 0.3), 2),
                    "duration_days": random.randint(5, 14)
                }
                
                endpoints_to_try = ["/groups", "/groups/create"]
                
                for endpoint in endpoints_to_try:
                    try:
                        response = requests.post(f"{BASE_URL}{endpoint}", 
                                               json=group_data, headers=headers)
                        if response.status_code in [200, 201]:
                            group = response.json()
                            self.groups.append(group)
                            print(f"   ✅ Grupo para {item['name']} creado")
                            break
                    except:
                        continue
                        
            except Exception as e:
                print(f"   ❌ Error creando grupo para {item['name']}: {e}")
        
        print(f"✅ {len(self.groups)} grupos creados")
    
    def create_interactions(self):
        """Crear interacciones usuario-item"""
        print("\n🔗 Creando interacciones usuario-item...")
        
        if not self.items or not self.tokens:
            print("❌ Necesitamos items y usuarios para crear interacciones")
            return
        
        interactions_created = 0
        
        for user_id, token in self.tokens.items():
            headers = {"Authorization": f"Bearer {token}"}
            
            # Cada usuario interactúa con algunos items aleatorios
            selected_items = random.sample(self.items, min(4, len(self.items)))
            
            for item in selected_items:
                try:
                    interaction_data = {
                        "interaction_type": random.choice(["view", "like", "purchase_intent"])
                    }
                    
                    # Intentar diferentes endpoints para interacciones
                    endpoints_to_try = [
                        f"/items/{item['id']}/interact",
                        f"/{item['id']}/interact",
                        f"/items/{item['id']}/interaction"
                    ]
                    
                    for endpoint in endpoints_to_try:
                        try:
                            response = requests.post(f"{BASE_URL}{endpoint}", 
                                                   json=interaction_data, headers=headers)
                            if response.status_code in [200, 201]:
                                interactions_created += 1
                                break
                        except:
                            continue
                            
                except Exception as e:
                    continue
        
        print(f"✅ {interactions_created} interacciones creadas")
    
    def test_recommendations(self):
        """Probar las recomendaciones GBGCN"""
        print("\n🤖 Probando recomendaciones GBGCN...")
        
        if not self.tokens:
            print("❌ No hay tokens para probar recomendaciones")
            return
        
        # Usar el primer token
        token = list(self.tokens.values())[0]
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            # Probar diferentes endpoints de recomendaciones
            endpoints_to_try = [
                "/recommendations",
                "/recommendations/items", 
                "/recommendations/groups",
                "/gbgcn"
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
                    if response.status_code == 200:
                        recommendations = response.json()
                        print(f"   ✅ {endpoint}: {len(recommendations)} recomendaciones")
                        
                        # Mostrar algunas recomendaciones
                        if isinstance(recommendations, list) and recommendations:
                            for i, rec in enumerate(recommendations[:2]):
                                if isinstance(rec, dict):
                                    name = rec.get('name', rec.get('title', 'Item'))
                                    score = rec.get('score', rec.get('recommendation_score', 'N/A'))
                                    print(f"      {i+1}. {name} - Score: {score}")
                    
                    elif response.status_code == 404:
                        print(f"   ⚠️ {endpoint}: Endpoint no encontrado")
                    else:
                        print(f"   ⚠️ {endpoint}: Error {response.status_code}")
                        
                except Exception as e:
                    print(f"   ❌ {endpoint}: {e}")
        
        except Exception as e:
            print(f"❌ Error probando recomendaciones: {e}")
    
    def show_summary(self):
        """Mostrar resumen de datos creados"""
        print(f"\n📊 RESUMEN DE DATOS CREADOS:")
        print("-" * 40)
        print(f"👥 Usuarios: {len(self.users)}")
        print(f"🛍️ Items: {len(self.items)}")
        print(f"👫 Grupos: {len(self.groups)}")
        print(f"🔑 Tokens: {len(self.tokens)}")
        
        print(f"\n🔑 CREDENCIALES PARA PRUEBAS:")
        print("-" * 40)
        if self.users:
            for user in self.users[:3]:  # Mostrar los primeros 3
                email = user.get('email', 'N/A')
                name = user.get('first_name', 'N/A')
                print(f"   👤 {name}: {email} / password123")
        
        print(f"\n🎯 PARA FLUTTER:")
        print("-" * 40)
        print(f"   🌐 Base URL: {BASE_URL}")
        print(f"   📖 Docs: http://127.0.0.1:8000/docs")
        
    def run(self):
        """Ejecutar creación completa de datos"""
        self.print_banner()
        
        print("⏳ Iniciando creación de datos...")
        time.sleep(1)
        
        self.create_users()
        time.sleep(1)
        
        self.create_items()
        time.sleep(1)
        
        self.create_groups()
        time.sleep(1)
        
        self.create_interactions()
        time.sleep(1)
        
        self.test_recommendations()
        
        self.show_summary()
        
        print(f"\n🎉 ¡DATOS DE MUESTRA CREADOS EXITOSAMENTE!")
        print("✅ El modelo GBGCN está listo para probar")
        print("📱 Puedes usar estos datos en tu app Flutter")

if __name__ == "__main__":
    creator = SampleDataCreator()
    creator.run() 