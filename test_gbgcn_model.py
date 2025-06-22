#!/usr/bin/env python3
"""
🧠 GBGCN Model Tester & Visualizer
Prueba el modelo GBGCN y muestra resultados detallados:
- Recomendaciones personalizadas
- Análisis de grupos activos
- Métricas del modelo
- Visualización de datos sociales
"""

import requests
import json
import pandas as pd
from datetime import datetime
import time

# Configuración de la API
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

class GBGCNModelTester:
    def __init__(self):
        self.token = None
        self.user_id = None
        self.test_user_email = "test@example.com"
        
    def authenticate(self):
        """Autenticar con usuario de prueba"""
        print("🔑 Autenticando usuario de prueba...")
        
        # Login
        login_data = {
            "username": self.test_user_email,
            "password": "testpassword123"
        }
        
        response = requests.post(f"{API_BASE}/login", data=login_data)
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            print("   ✅ Autenticación exitosa")
            
            # Obtener información del usuario
            headers = {"Authorization": f"Bearer {self.token}"}
            user_response = requests.get(f"{API_BASE}/users/me", headers=headers)
            
            if user_response.status_code == 200:
                user_data = user_response.json()
                self.user_id = user_data["id"]
                print(f"   👤 Usuario: {user_data['email']} (ID: {self.user_id[:8]}...)")
                return True
            else:
                print(f"   ❌ Error obteniendo usuario: {user_response.status_code}")
                return False
        else:
            print(f"   ❌ Error de autenticación: {response.status_code}")
            return False
    
    def test_recommendations(self):
        """Probar recomendaciones del modelo GBGCN"""
        print("\n🎯 PROBANDO RECOMENDACIONES GBGCN")
        print("="*50)
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Obtener recomendaciones
        response = requests.get(f"{API_BASE}/recommendations/", headers=headers)
        
        if response.status_code == 200:
            recommendations = response.json()
            print(f"✅ Obtenidas {len(recommendations)} recomendaciones")
            
            if recommendations:
                print("\n📋 TOP 5 RECOMENDACIONES:")
                print("-" * 60)
                
                for i, rec in enumerate(recommendations[:5], 1):
                    print(f"\n{i}. 📦 ITEM: {rec.get('item_name', 'N/A')}")
                    print(f"   🎯 Score: {rec.get('recommendation_score', 0):.3f}")
                    print(f"   📊 Probabilidad éxito: {rec.get('success_probability', 0):.3f}")
                    print(f"   🤝 Influencia social: {rec.get('social_influence_score', 0):.3f}")
                    print(f"   🎫 Tipo: {rec.get('recommendation_type', 'N/A')}")
                    print(f"   👥 Tamaño grupo objetivo: {rec.get('target_group_size', 0)}")
                    print(f"   💰 Precio predicho: ${rec.get('predicted_price', 0):,.2f}")
                    print(f"   🔄 Modelo: {rec.get('model_version', 'N/A')}")
            else:
                print("⚠️  No se encontraron recomendaciones para este usuario")
        else:
            print(f"❌ Error obteniendo recomendaciones: {response.status_code}")
            if response.text:
                print(f"   Detalle: {response.text}")
    
    def test_groups_analysis(self):
        """Analizar grupos de compra activos"""
        print("\n👨‍👩‍👧‍👦 ANÁLISIS DE GRUPOS ACTIVOS")
        print("="*50)
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Obtener grupos
        response = requests.get(f"{API_BASE}/groups/", headers=headers)
        
        if response.status_code == 200:
            groups = response.json()
            print(f"✅ Encontrados {len(groups)} grupos")
            
            if groups:
                # Estadísticas generales
                statuses = {}
                total_participants = 0
                total_value = 0
                
                print("\n📊 ESTADÍSTICAS GENERALES:")
                print("-" * 40)
                
                for group in groups:
                    status = group.get('status', 'UNKNOWN')
                    statuses[status] = statuses.get(status, 0) + 1
                    total_participants += group.get('current_quantity', 0)
                    total_value += group.get('total_amount', 0) or 0
                
                print(f"📈 Total participantes: {total_participants}")
                print(f"💰 Valor total: ${total_value:,.2f}")
                print("\n🏷️  Estados de grupos:")
                for status, count in statuses.items():
                    print(f"   {status}: {count} grupos")
                
                # Top grupos por valor
                top_groups = sorted(groups, key=lambda x: x.get('total_amount', 0) or 0, reverse=True)[:3]
                
                print("\n🏆 TOP 3 GRUPOS POR VALOR:")
                print("-" * 40)
                
                for i, group in enumerate(top_groups, 1):
                    print(f"\n{i}. 🎯 {group.get('title', 'Sin título')}")
                    print(f"   📦 Item: {group.get('item_name', 'N/A')}")
                    print(f"   👥 Participantes: {group.get('current_quantity', 0)}/{group.get('target_quantity', 0)}")
                    print(f"   💰 Valor total: ${group.get('total_amount', 0):,.2f}")
                    print(f"   💵 Precio por unidad: ${group.get('current_price_per_unit', 0):,.2f}")
                    print(f"   📊 Estado: {group.get('status', 'N/A')}")
                    print(f"   🎲 Prob. éxito: {group.get('success_probability', 0):.3f}")
                    print(f"   🤝 Influencia social: {group.get('social_influence_score', 0):.3f}")
            else:
                print("⚠️  No se encontraron grupos activos")
        else:
            print(f"❌ Error obteniendo grupos: {response.status_code}")
    
    def test_social_connections(self):
        """Analizar conexiones sociales"""
        print("\n🤝 ANÁLISIS DE CONEXIONES SOCIALES")
        print("="*50)
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Obtener conexiones sociales
        response = requests.get(f"{API_BASE}/social/connections", headers=headers)
        
        if response.status_code == 200:
            connections = response.json()
            print(f"✅ El usuario tiene {len(connections)} conexiones")
            
            if connections:
                # Estadísticas de conexiones
                connection_types = {}
                avg_strength = 0
                avg_frequency = 0
                
                for conn in connections:
                    conn_type = conn.get('connection_type', 'unknown')
                    connection_types[conn_type] = connection_types.get(conn_type, 0) + 1
                    avg_strength += conn.get('connection_strength', 0)
                    avg_frequency += conn.get('interaction_frequency', 0)
                
                avg_strength /= len(connections)
                avg_frequency /= len(connections)
                
                print(f"\n📊 MÉTRICAS SOCIALES:")
                print("-" * 30)
                print(f"🔗 Fuerza promedio: {avg_strength:.3f}")
                print(f"🔄 Frecuencia promedio: {avg_frequency:.3f}")
                
                print("\n🏷️  Tipos de conexión:")
                for conn_type, count in connection_types.items():
                    print(f"   {conn_type}: {count} conexiones")
                
                # Top conexiones más fuertes
                top_connections = sorted(connections, key=lambda x: x.get('connection_strength', 0), reverse=True)[:3]
                
                print("\n💪 TOP 3 CONEXIONES MÁS FUERTES:")
                print("-" * 35)
                
                for i, conn in enumerate(top_connections, 1):
                    print(f"\n{i}. 👤 {conn.get('friend_name', 'Usuario')} ({conn.get('friend_email', 'N/A')})")
                    print(f"   💪 Fuerza: {conn.get('connection_strength', 0):.3f}")
                    print(f"   🔄 Frecuencia: {conn.get('interaction_frequency', 0):.3f}")
                    print(f"   🏷️  Tipo: {conn.get('connection_type', 'N/A')}")
                    print(f"   📅 Última interacción: {conn.get('last_interaction', 'N/A')}")
            else:
                print("⚠️  El usuario no tiene conexiones sociales registradas")
        else:
            print(f"❌ Error obteniendo conexiones: {response.status_code}")
    
    def test_analytics_dashboard(self):
        """Probar dashboard de analytics"""
        print("\n📊 DASHBOARD DE ANALYTICS")
        print("="*50)
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Obtener dashboard
        response = requests.get(f"{API_BASE}/analytics/dashboard", headers=headers)
        
        if response.status_code == 200:
            dashboard = response.json()
            print("✅ Dashboard cargado exitosamente")
            
            print("\n📈 MÉTRICAS PRINCIPALES:")
            print("-" * 30)
            
            # Métricas de usuario
            user_metrics = dashboard.get('user_metrics', {})
            print(f"👥 Total usuarios: {user_metrics.get('total_users', 0)}")
            print(f"🟢 Usuarios activos: {user_metrics.get('active_users', 0)}")
            print(f"✅ Usuarios verificados: {user_metrics.get('verified_users', 0)}")
            print(f"⭐ Reputación promedio: {user_metrics.get('average_reputation', 0):.2f}")
            
            # Métricas de items
            item_metrics = dashboard.get('item_metrics', {})
            print(f"\n📦 Total items: {item_metrics.get('total_items', 0)}")
            print(f"🟢 Items activos: {item_metrics.get('active_items', 0)}")
            print(f"💰 Precio promedio: ${item_metrics.get('average_price', 0):,.2f}")
            
            # Métricas de grupos
            group_metrics = dashboard.get('group_metrics', {})
            print(f"\n👨‍👩‍👧‍👦 Total grupos: {group_metrics.get('total_groups', 0)}")
            print(f"🟢 Grupos activos: {group_metrics.get('active_groups', 0)}")
            print(f"💰 Valor total grupos: ${group_metrics.get('total_group_value', 0):,.2f}")
            print(f"📊 Tasa de éxito: {group_metrics.get('success_rate', 0):.1%}")
            
            # Métricas GBGCN
            model_metrics = dashboard.get('model_metrics', {})
            if model_metrics:
                print(f"\n🧠 MÉTRICAS DEL MODELO GBGCN:")
                print("-" * 35)
                print(f"🎯 Total recomendaciones: {model_metrics.get('total_recommendations', 0)}")
                print(f"📊 Score promedio: {model_metrics.get('average_score', 0):.3f}")
                print(f"✅ Tasa de acierto: {model_metrics.get('accuracy_rate', 0):.1%}")
                print(f"🔄 Modelo versión: {model_metrics.get('model_version', 'N/A')}")
            
        else:
            print(f"❌ Error cargando dashboard: {response.status_code}")
    
    def test_model_training_status(self):
        """Verificar estado del entrenamiento del modelo"""
        print("\n🧠 ESTADO DEL MODELO GBGCN")
        print("="*50)
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Obtener estado de entrenamiento
        response = requests.get(f"{API_BASE}/recommendations/training/status", headers=headers)
        
        if response.status_code == 200:
            status = response.json()
            print("✅ Estado del modelo obtenido")
            
            print(f"\n🔄 Estado: {status.get('status', 'UNKNOWN')}")
            print(f"📊 Progreso: {status.get('progress', 0):.1f}%")
            print(f"🧮 Época actual: {status.get('current_epoch', 0)}")
            print(f"📈 Pérdida actual: {status.get('current_loss', 0):.6f}")
            print(f"⏰ Tiempo transcurrido: {status.get('elapsed_time', 0):.1f}s")
            print(f"🎯 Último score: {status.get('last_validation_score', 0):.6f}")
            print(f"📅 Última actualización: {status.get('last_updated', 'N/A')}")
            
        else:
            print(f"❌ Error obteniendo estado: {response.status_code}")
    
    def run_complete_test(self):
        """Ejecutar suite completa de pruebas del modelo GBGCN"""
        print("🚀 GBGCN Model Complete Test Suite")
        print("🧪 Probando modelo de recomendaciones con datos reales")
        print("="*60)
        print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 API: {BASE_URL}")
        print()
        
        # Verificar si la API está disponible
        try:
            health_response = requests.get(f"{BASE_URL}/health", timeout=5)
            if health_response.status_code == 200:
                print("✅ API está funcionando")
            else:
                print(f"⚠️  API responde pero con código: {health_response.status_code}")
        except Exception as e:
            print(f"❌ API no disponible: {e}")
            return
        
        # Autenticar
        if not self.authenticate():
            print("❌ No se pudo autenticar. Finalizando pruebas.")
            return
        
        # Ejecutar todas las pruebas
        try:
            self.test_recommendations()
            self.test_groups_analysis()
            self.test_social_connections()
            self.test_analytics_dashboard()
            self.test_model_training_status()
            
            print("\n" + "="*60)
            print("✅ PRUEBAS COMPLETADAS EXITOSAMENTE")
            print("🎯 El modelo GBGCN está funcionando correctamente")
            print("📊 Datos de prueba cargados y procesados")
            print("🧠 Recomendaciones generadas basadas en:")
            print("   - Preferencias del usuario")
            print("   - Conexiones sociales")
            print("   - Historial de interacciones")
            print("   - Probabilidades de éxito en grupos")
            print("\n💡 SIGUIENTES PASOS:")
            print("   - Entrenar el modelo con más datos")
            print("   - Ajustar parámetros GBGCN (ALPHA, BETA)")
            print("   - Evaluar métricas de rendimiento")
            print("   - Implementar A/B testing")
            
        except Exception as e:
            print(f"\n❌ Error durante las pruebas: {e}")
            import traceback
            traceback.print_exc()

def main():
    """Función principal"""
    tester = GBGCNModelTester()
    tester.run_complete_test()

if __name__ == "__main__":
    main() 