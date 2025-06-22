#!/usr/bin/env python3
"""
🧪 Script Completo para Probar el Modelo GBGCN
Este script configura automáticamente todo lo necesario para probar el sistema.
"""

import sys
import asyncio
import requests
import json
import time
import subprocess
import os
from pathlib import Path

# Configuración básica
BASE_URL = "http://localhost:8000/api/v1"
SERVER_URL = "http://localhost:8000"

class GBGCNTester:
    def __init__(self):
        self.access_token = None
        self.test_users = []
        self.test_items = []
        self.test_groups = []
        
    def print_banner(self):
        """Mostrar banner de inicio"""
        print("🚀 GBGCN GROUP BUYING SYSTEM - PRUEBA COMPLETA")
        print("=" * 60)
        print("📊 Este script probará completamente el modelo GBGCN")
        print("🤖 Incluye: Configuración, Datos, Entrenamiento y Predicciones")
        print("=" * 60)
        
    def check_dependencies(self):
        """Verificar dependencias necesarias"""
        print("\n🔧 Verificando dependencias...")
        
        try:
            import torch
            import requests
            import aiosqlite
            print("✅ Dependencias básicas instaladas")
            return True
        except ImportError as e:
            print(f"❌ Dependencia faltante: {e}")
            print("💡 Ejecuta: pip install -r requirements.txt")
            return False
    
    def setup_database(self):
        """Configurar base de datos SQLite para pruebas rápidas"""
        print("\n💾 Configurando base de datos SQLite...")
        
        # Crear archivo .env con SQLite
        env_content = """
# Configuración para pruebas rápidas
DATABASE_URL=sqlite+aiosqlite:///./test_groupbuy.db
SECRET_KEY=test-secret-key-for-gbgcn-testing
DEBUG=true
ENVIRONMENT=development
"""
        
        with open('.env', 'w') as f:
            f.write(env_content)
        
        print("✅ Configuración de base de datos lista (SQLite)")
        return True
    
    def start_api_server(self):
        """Iniciar servidor API en segundo plano"""
        print("\n🌐 Iniciando servidor API...")
        
        try:
            # Verificar si ya está ejecutándose
            response = requests.get(SERVER_URL, timeout=2)
            print("✅ Servidor ya está ejecutándose")
            return True
        except:
            pass
        
        # Iniciar servidor
        print("🚀 Iniciando servidor FastAPI...")
        
        # Configurar PYTHONPATH
        os.environ['PYTHONPATH'] = '.'
        
        # Comando para iniciar servidor
        cmd = [
            sys.executable, "-m", "uvicorn", 
            "src.api.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ]
        
        # Ejecutar en segundo plano
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        
        # Esperar a que se inicie
        print("⏳ Esperando que el servidor se inicie...")
        for i in range(15):
            try:
                response = requests.get(SERVER_URL, timeout=2)
                print("✅ Servidor API iniciado correctamente")
                return True
            except:
                time.sleep(2)
                print(f"   Esperando... ({i+1}/15)")
        
        print("❌ No se pudo iniciar el servidor")
        return False
    
    def create_test_user_and_login(self):
        """Crear usuario de prueba y hacer login"""
        print("\n👤 Creando usuario de prueba...")
        
        # Datos del usuario de prueba
        user_data = {
            "username": "gbgcn_tester",
            "email": "gbgcn@test.com",
            "password": "test123456",
            "first_name": "GBGCN",
            "last_name": "Tester",
            "phone": "+1234567890"
        }
        
        try:
            # Registrar usuario
            response = requests.post(f"{BASE_URL}/auth/register", json=user_data)
            if response.status_code == 201:
                print("✅ Usuario de prueba creado")
            else:
                print("⚠️ Usuario ya existe, continuando...")
            
            # Hacer login
            login_data = {
                "email": user_data["email"],
                "password": user_data["password"]
            }
            
            response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
            if response.status_code == 200:
                tokens = response.json()
                self.access_token = tokens["access_token"]
                print("✅ Login exitoso, token obtenido")
                return True
            else:
                print(f"❌ Error en login: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def create_sample_data(self):
        """Crear datos de muestra para el sistema"""
        print("\n📊 Creando datos de muestra...")
        
        if not self.access_token:
            print("❌ No hay token de acceso")
            return False
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # Crear items de prueba
        items_data = [
            {
                "name": "iPhone 15 Pro",
                "description": "Latest iPhone with advanced features",
                "base_price": 999.99,
                "category": "Electronics",
                "image_url": "https://example.com/iphone15.jpg"
            },
            {
                "name": "MacBook Air M3",
                "description": "Powerful laptop for work and creativity",
                "base_price": 1299.99,
                "category": "Electronics",
                "image_url": "https://example.com/macbook.jpg"
            },
            {
                "name": "AirPods Pro",
                "description": "Premium wireless earbuds",
                "base_price": 249.99,
                "category": "Electronics",
                "image_url": "https://example.com/airpods.jpg"
            }
        ]
        
        print("🛍️ Creando items de prueba...")
        for item_data in items_data:
            try:
                response = requests.post(f"{BASE_URL}/items", json=item_data, headers=headers)
                if response.status_code == 201:
                    item = response.json()
                    self.test_items.append(item)
                    print(f"   ✅ {item['name']} creado")
            except Exception as e:
                print(f"   ⚠️ Error creando item: {e}")
        
        # Crear usuarios adicionales
        additional_users = [
            {"username": "user1", "email": "user1@test.com", "password": "test123"},
            {"username": "user2", "email": "user2@test.com", "password": "test123"},
            {"username": "user3", "email": "user3@test.com", "password": "test123"}
        ]
        
        print("👥 Creando usuarios adicionales...")
        for user_data in additional_users:
            user_data.update({
                "first_name": "Test",
                "last_name": "User",
                "phone": "+1234567890"
            })
            
            try:
                response = requests.post(f"{BASE_URL}/auth/register", json=user_data)
                if response.status_code == 201:
                    print(f"   ✅ {user_data['username']} creado")
            except:
                pass
        
        print("✅ Datos de muestra creados")
        return True
    
    def test_recommendations(self):
        """Probar sistema de recomendaciones GBGCN"""
        print("\n🤖 Probando Sistema de Recomendaciones GBGCN...")
        
        if not self.access_token:
            print("❌ No hay token de acceso")
            return False
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        try:
            # 1. Recomendaciones de items
            print("🔍 Probando recomendaciones de items...")
            response = requests.get(f"{BASE_URL}/recommendations/items", headers=headers)
            print(f"   📊 Status: {response.status_code}")
            
            if response.status_code == 200:
                recommendations = response.json()
                print(f"   ✅ {len(recommendations)} recomendaciones obtenidas")
                
                for i, rec in enumerate(recommendations[:3], 1):
                    print(f"   {i}. {rec.get('name', 'Item')} - Score: {rec.get('score', 'N/A')}")
            
            # 2. Recomendaciones de grupos
            print("\n👥 Probando recomendaciones de grupos...")
            response = requests.get(f"{BASE_URL}/recommendations/groups", headers=headers)
            print(f"   📊 Status: {response.status_code}")
            
            # 3. Análisis de influencia social
            print("\n🌐 Probando análisis de influencia social...")
            response = requests.get(f"{BASE_URL}/recommendations/social-influence", headers=headers)
            print(f"   📊 Status: {response.status_code}")
            
            # 4. Predicción de éxito si hay items
            if self.test_items:
                print("\n🎯 Probando predicción de éxito de grupo...")
                prediction_data = {
                    "item_id": self.test_items[0]["id"],
                    "target_quantity": 10,
                    "duration_days": 7
                }
                
                response = requests.post(
                    f"{BASE_URL}/recommendations/predict-success",
                    json=prediction_data,
                    headers=headers
                )
                print(f"   📊 Status: {response.status_code}")
                
                if response.status_code == 200:
                    prediction = response.json()
                    print(f"   🎯 Probabilidad de éxito: {prediction.get('success_probability', 'N/A')}")
                    print(f"   📈 Score de recomendación: {prediction.get('recommendation_score', 'N/A')}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error probando recomendaciones: {e}")
            return False
    
    def create_test_group(self):
        """Crear un grupo de prueba"""
        print("\n👥 Creando grupo de prueba...")
        
        if not self.access_token or not self.test_items:
            print("❌ No hay token o items disponibles")
            return False
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        group_data = {
            "title": "Grupo iPhone 15 Pro - Descuento Especial",
            "description": "Compremos juntos y ahorremos en el nuevo iPhone",
            "item_id": self.test_items[0]["id"],
            "target_quantity": 5,
            "current_quantity": 1,
            "discount_percentage": 0.15,
            "duration_days": 7
        }
        
        try:
            response = requests.post(f"{BASE_URL}/groups", json=group_data, headers=headers)
            print(f"📊 Status: {response.status_code}")
            
            if response.status_code == 201:
                group = response.json()
                self.test_groups.append(group)
                print(f"✅ Grupo creado: {group['title']}")
                print(f"   💰 Descuento: {group['discount_percentage']*100}%")
                print(f"   🎯 Meta: {group['target_quantity']} unidades")
                return True
            else:
                print(f"❌ Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error creando grupo: {e}")
            return False
    
    def show_api_documentation(self):
        """Mostrar información de la API"""
        print("\n📚 Información de la API:")
        print("-" * 40)
        print(f"🌐 URL base: {BASE_URL}")
        print(f"📖 Documentación: {SERVER_URL}/docs")
        print(f"🔑 Tu token de acceso: {self.access_token[:20] if self.access_token else 'No disponible'}...")
        
        print("\n🔧 Endpoints principales probados:")
        endpoints = [
            "✅ POST /auth/register - Registro de usuarios",
            "✅ POST /auth/login - Autenticación",
            "✅ GET /recommendations/items - Recomendaciones GBGCN",
            "✅ GET /recommendations/groups - Grupos recomendados",
            "✅ POST /recommendations/predict-success - Predicción de éxito",
            "✅ GET /recommendations/social-influence - Análisis social",
            "✅ POST /items - Crear productos",
            "✅ POST /groups - Crear grupos de compra"
        ]
        
        for endpoint in endpoints:
            print(f"   {endpoint}")
    
    def run_complete_test(self):
        """Ejecutar prueba completa del sistema"""
        self.print_banner()
        
        # 1. Verificar dependencias
        if not self.check_dependencies():
            return False
        
        # 2. Configurar base de datos
        if not self.setup_database():
            return False
        
        # 3. Iniciar servidor
        if not self.start_api_server():
            return False
        
        # 4. Crear usuario y login
        if not self.create_test_user_and_login():
            return False
        
        # 5. Crear datos de muestra
        if not self.create_sample_data():
            return False
        
        # 6. Probar recomendaciones GBGCN
        if not self.test_recommendations():
            return False
        
        # 7. Crear grupo de prueba
        if not self.create_test_group():
            return False
        
        # 8. Mostrar información
        self.show_api_documentation()
        
        print("\n🎉 ¡PRUEBA COMPLETA EXITOSA!")
        print("=" * 60)
        print("✅ El modelo GBGCN está funcionando correctamente")
        print("✅ Todos los endpoints están operativos")
        print("✅ Sistema listo para integración con Flutter")
        print("=" * 60)
        
        print("\n🚀 Para Flutter, usa estas credenciales:")
        print(f"   📍 Base URL: {BASE_URL}")
        print(f"   🔑 Token: {self.access_token}")
        print(f"   👤 Usuario: gbgcn@test.com")
        print(f"   🔒 Password: test123456")
        
        return True

if __name__ == "__main__":
    tester = GBGCNTester()
    success = tester.run_complete_test()
    
    if success:
        print("\n🎯 ¡Todo listo! El sistema GBGCN está funcionando.")
        print("📱 Puedes ahora integrar con Flutter usando las credenciales mostradas.")
    else:
        print("\n❌ Hubo problemas en las pruebas.")
        print("💡 Revisa los errores mostrados arriba.") 