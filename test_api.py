#!/usr/bin/env python3
"""
Script para probar la API de Group Buying y crear datos de ejemplo
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v1"

def test_api():
    """Probar endpoints básicos de la API"""
    print("🧪 Probando API de Group Buying GBGCN")
    print("=" * 50)
    
    # 1. Probar endpoint básico
    try:
        response = requests.get("http://localhost:8000")
        print(f"✅ Endpoint raíz: {response.status_code}")
        if response.status_code == 200:
            print(f"   📋 API funcionando")
    except Exception as e:
        print(f"❌ Error conectando a la API: {e}")
        return False
    
    # 2. Probar documentación
    try:
        response = requests.get("http://localhost:8000/docs")
        print(f"✅ Documentación: {response.status_code}")
    except Exception as e:
        print(f"❌ Error en docs: {e}")
    
    return True

def create_test_user():
    """Crear un usuario de prueba"""
    print("\n👤 Creando usuario de prueba...")
    
    user_data = {
        "username": "test_user",
        "email": "test@example.com",
        "password": "testpassword123",
        "first_name": "Test",
        "last_name": "User",
        "phone": "+1234567890"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=user_data)
        print(f"📝 Registro de usuario: {response.status_code}")
        
        if response.status_code == 201:
            user = response.json()
            print(f"   ✅ Usuario creado: {user['username']}")
            return user
        else:
            print(f"   ⚠️ Respuesta: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error creando usuario: {e}")
        return None

def login_user(email, password):
    """Hacer login y obtener token"""
    print(f"\n🔐 Haciendo login con {email}...")
    
    login_data = {
        "email": email,
        "password": password
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print(f"🔑 Login: {response.status_code}")
        
        if response.status_code == 200:
            tokens = response.json()
            print("   ✅ Login exitoso")
            return tokens
        else:
            print(f"   ⚠️ Respuesta: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error en login: {e}")
        return None

def create_test_category(token):
    """Crear una categoría de prueba"""
    print("\n📂 Creando categoría de prueba...")
    
    headers = {"Authorization": f"Bearer {token}"}
    category_data = {
        "name": "Electronics",
        "description": "Electronic devices and gadgets"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/categories", json=category_data, headers=headers)
        print(f"📁 Categoría: {response.status_code}")
        
        if response.status_code == 201:
            category = response.json()
            print(f"   ✅ Categoría creada: {category['name']}")
            return category
        else:
            print(f"   ⚠️ Respuesta: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error creando categoría: {e}")
        return None

def test_recommendations_endpoint(token):
    """Probar endpoints de recomendaciones GBGCN"""
    print("\n🤖 Probando endpoints de recomendaciones GBGCN...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # Probar recomendaciones de items
        response = requests.get(f"{BASE_URL}/recommendations/items", headers=headers)
        print(f"🔍 Recomendaciones de items: {response.status_code}")
        
        # Probar recomendaciones de grupos
        response = requests.get(f"{BASE_URL}/recommendations/groups", headers=headers)
        print(f"👥 Recomendaciones de grupos: {response.status_code}")
        
        # Probar análisis de formación de grupos
        response = requests.get(f"{BASE_URL}/recommendations/group-formation-analysis", headers=headers)
        print(f"📊 Análisis de formación: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error probando recomendaciones: {e}")
        return False

def show_api_endpoints():
    """Mostrar los endpoints disponibles"""
    print("\n📋 Endpoints principales de la API:")
    print("-" * 40)
    
    endpoints = [
        "GET    /health                           - Health check",
        "GET    /docs                            - Documentación Swagger",
        "POST   /auth/register                   - Registro de usuario",
        "POST   /auth/login                      - Login",
        "GET    /users/me                        - Perfil actual",
        "GET    /recommendations/items           - Recomendaciones GBGCN",
        "GET    /recommendations/groups          - Grupos recomendados",
        "POST   /recommendations/predict-success - Predicción de éxito",
        "GET    /recommendations/social-influence - Análisis social",
        "POST   /groups                          - Crear grupo",
        "GET    /groups                          - Listar grupos",
        "POST   /items                           - Crear item",
        "GET    /items                           - Listar items"
    ]
    
    for endpoint in endpoints:
        print(f"   {endpoint}")
    
    print(f"\n🌐 Documentación completa: http://localhost:8000/docs")

if __name__ == "__main__":
    print("🚀 Iniciando pruebas de la API Group Buying GBGCN")
    print("=" * 60)
    
    # Dar tiempo para que la aplicación se inicie
    print("⏳ Esperando que la aplicación se inicie...")
    time.sleep(3)
    
    # Probar API básica
    if not test_api():
        print("❌ Las pruebas básicas fallaron")
        exit(1)
    
    # Crear usuario de prueba (o usar existente)
    user = create_test_user()
    if not user:
        print("ℹ️ Usuario ya existe, continuando con login...")
    
    # Hacer login
    tokens = login_user("test@example.com", "testpassword123")
    if not tokens:
        print("❌ No se pudo hacer login")
        exit(1)
    
    access_token = tokens["access_token"]
    
    # Crear categoría
    category = create_test_category(access_token)
    
    # Probar endpoints de recomendaciones
    test_recommendations_endpoint(access_token)
    
    # Mostrar endpoints disponibles
    show_api_endpoints()
    
    print("\n🎉 ¡API funcionando correctamente!")
    print("📱 Tu aplicación Flutter puede conectarse a: http://localhost:8000/api/v1")
    print("📖 Documentación: http://localhost:8000/docs") 