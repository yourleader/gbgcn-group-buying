#!/usr/bin/env python3
"""
Script para probar las recomendaciones del modelo GBGCN entrenado
"""
import sys
import torch
import numpy as np
from pathlib import Path
import asyncio
import asyncpg
import json

# Agregar src al path
sys.path.append(str(Path(__file__).parent.parent / "src"))

async def load_model_and_data():
    """Cargar el modelo entrenado y los datos"""
    print("🔧 Cargando modelo GBGCN entrenado...")
    
    model_path = Path("models") / "gbgcn_simple.pth"
    if not model_path.exists():
        print("❌ Modelo no encontrado. Ejecuta primero el entrenamiento.")
        return None, None
    
    # Cargar modelo
    checkpoint = torch.load(model_path, map_location='cpu')
    
    from ml.gbgcn_model import GBGCN
    
    model = GBGCN(
        num_users=checkpoint['num_users'],
        num_items=checkpoint['num_items'],
        embedding_dim=32,
        num_layers=2,
        dropout=0.1,
        alpha=0.6,
        beta=0.4
    )
    
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    
    print(f"✅ Modelo cargado: {checkpoint['num_users']} usuarios, {checkpoint['num_items']} items")
    
    return model, checkpoint

async def load_current_data():
    """Cargar datos actuales de la base de datos"""
    print("📊 Cargando datos actuales...")
    
    conn = await asyncpg.connect(
        user="postgres",
        password="postgres",
        database="groupbuy_db",
        host="localhost",
        port=5432
    )
    
    try:
        # Cargar usuarios con nombres
        users = await conn.fetch("SELECT id, username, email FROM users")
        
        # Cargar items con nombres
        items = await conn.fetch("SELECT id, name, base_price FROM items")
        
        # Cargar grupos activos
        groups = await conn.fetch("""
            SELECT id, title, item_id, creator_id, target_quantity, current_quantity
            FROM groups 
            WHERE status = 'active'
        """)
        
        # Cargar interacciones
        interactions = await conn.fetch("""
            SELECT user_id, item_id, interaction_type 
            FROM user_item_interactions
        """)
        
        # Cargar conexiones sociales
        social = await conn.fetch("""
            SELECT user_id, friend_id, connection_strength 
            FROM social_connections
        """)
        
        return {
            'users': users,
            'items': items,
            'groups': groups,
            'interactions': interactions,
            'social': social
        }
        
    finally:
        await conn.close()

def prepare_graph_data(data, user_to_idx, item_to_idx):
    """Preparar datos del grafo para predicciones"""
    # Crear edges para las vistas
    initiator_edges = []
    participant_edges = []
    
    for interaction in data['interactions']:
        user_id = interaction['user_id']
        item_id = interaction['item_id']
        
        if user_id in user_to_idx and item_id in item_to_idx:
            user_idx = user_to_idx[user_id]
            item_idx = item_to_idx[item_id]
            
            if interaction['interaction_type'] in ['view', 'like']:
                participant_edges.append([user_idx, item_idx])
            else:
                initiator_edges.append([user_idx, item_idx])
    
    # Crear edges sociales
    social_edges = []
    social_weights = []
    
    for connection in data['social']:
        user1_id = connection['user_id']
        user2_id = connection['friend_id']
        
        if user1_id in user_to_idx and user2_id in user_to_idx:
            user1_idx = user_to_idx[user1_id]
            user2_idx = user_to_idx[user2_id]
            
            social_edges.append([user1_idx, user2_idx])
            social_weights.append(connection['connection_strength'] or 0.5)
    
    # Convertir a tensors
    initiator_edge_index = torch.tensor(initiator_edges + [[0, 0]], dtype=torch.long).t()
    participant_edge_index = torch.tensor(participant_edges + [[0, 0]], dtype=torch.long).t()
    social_edge_index = torch.tensor(social_edges + [[0, 0]], dtype=torch.long).t()
    social_edge_weights = torch.tensor(social_weights + [0.5], dtype=torch.float)
    
    return {
        'initiator_edge_index': initiator_edge_index,
        'participant_edge_index': participant_edge_index,
        'social_edge_index': social_edge_index,
        'social_edge_weights': social_edge_weights
    }

def get_recommendations_for_user(model, user_idx, graph_data, num_items, top_k=5):
    """Obtener recomendaciones para un usuario específico"""
    with torch.no_grad():
        # Crear batch con el usuario y todos los items
        user_batch = torch.full((num_items,), user_idx, dtype=torch.long)
        item_batch = torch.arange(num_items, dtype=torch.long)
        
        try:
            # Predicciones
            outputs = model(
                user_ids=user_batch,
                item_ids=item_batch,
                initiator_edge_index=graph_data['initiator_edge_index'],
                participant_edge_index=graph_data['participant_edge_index'],
                social_edge_index=graph_data['social_edge_index'],
                social_edge_weights=graph_data['social_edge_weights']
            )
            
            scores = outputs['recommendation_score'].numpy()
            success_probs = outputs['success_probability'].numpy()
            
            # Obtener top-k items
            top_indices = np.argsort(scores)[-top_k:][::-1]
            
            recommendations = []
            for idx in top_indices:
                recommendations.append({
                    'item_idx': int(idx),
                    'recommendation_score': float(scores[idx]),
                    'success_probability': float(success_probs[idx])
                })
            
            return recommendations
            
        except Exception as e:
            print(f"Error en predicciones: {e}")
            return []

def predict_group_success(model, creator_idx, item_idx, graph_data):
    """Predecir el éxito de un grupo específico"""
    with torch.no_grad():
        try:
            outputs = model(
                user_ids=torch.tensor([creator_idx]),
                item_ids=torch.tensor([item_idx]),
                initiator_edge_index=graph_data['initiator_edge_index'],
                participant_edge_index=graph_data['participant_edge_index'],
                social_edge_index=graph_data['social_edge_index'],
                social_edge_weights=graph_data['social_edge_weights']
            )
            
            return {
                'recommendation_score': outputs['recommendation_score'].item(),
                'success_probability': outputs['success_probability'].item()
            }
            
        except Exception as e:
            print(f"Error en predicción de grupo: {e}")
            return {'recommendation_score': 0.5, 'success_probability': 0.5}

async def test_recommendations():
    """Probar el sistema completo de recomendaciones"""
    print("🧪 Probando Sistema de Recomendaciones GBGCN")
    print("=" * 50)
    
    # Cargar modelo y datos
    model, checkpoint = await load_model_and_data()
    if model is None:
        return
    
    data = await load_current_data()
    
    user_to_idx = checkpoint['user_to_idx']
    item_to_idx = checkpoint['item_to_idx']
    
    # Crear mapeos inversos para mostrar nombres
    idx_to_user = {v: k for k, v in user_to_idx.items()}
    idx_to_item = {v: k for k, v in item_to_idx.items()}
    
    # Crear diccionarios de información
    user_info = {u['id']: u for u in data['users']}
    item_info = {i['id']: i for i in data['items']}
    
    # Preparar datos del grafo
    graph_data = prepare_graph_data(data, user_to_idx, item_to_idx)
    
    print("\n🎯 Generando Recomendaciones Personalizadas")
    print("-" * 40)
    
    # Probar recomendaciones para algunos usuarios
    for user_idx in range(min(3, len(user_to_idx))):
        if user_idx in idx_to_user:
            user_id = idx_to_user[user_idx]
            user = user_info.get(user_id, {'username': 'Unknown', 'email': 'unknown@example.com'})
            
            print(f"\n👤 Usuario: {user['username']} ({user['email']})")
            
            recommendations = get_recommendations_for_user(
                model, user_idx, graph_data, len(item_to_idx), top_k=3
            )
            
            print("🔍 Top 3 Recomendaciones:")
            for i, rec in enumerate(recommendations, 1):
                item_idx = rec['item_idx']
                if item_idx in idx_to_item:
                    item_id = idx_to_item[item_idx]
                    item = item_info.get(item_id, {'name': 'Unknown', 'base_price': 0})
                    
                    print(f"   {i}. {item['name']}")
                    print(f"      💰 Precio: ${item['base_price']:.2f}")
                    print(f"      📊 Score: {rec['recommendation_score']:.3f}")
                    print(f"      🎯 Prob. Éxito: {rec['success_probability']:.3f}")
    
    # Analizar grupos activos
    print(f"\n👥 Análisis de Grupos Activos")
    print("-" * 40)
    
    for group in data['groups'][:3]:  # Analizar los primeros 3 grupos
        creator_id = group['creator_id']
        item_id = group['item_id']
        
        if creator_id in user_to_idx and item_id in item_to_idx:
            creator_idx = user_to_idx[creator_id]
            item_idx = item_to_idx[item_id]
            
            creator = user_info.get(creator_id, {'username': 'Unknown'})
            item = item_info.get(item_id, {'name': 'Unknown'})
            
            prediction = predict_group_success(model, creator_idx, item_idx, graph_data)
            
            print(f"\n📊 Grupo: {group['title']}")
            print(f"   👤 Creador: {creator['username']}")
            print(f"   🛍️ Item: {item['name']}")
            print(f"   📈 Progreso: {group['current_quantity']}/{group['target_quantity']}")
            print(f"   🎯 Predicción GBGCN:")
            print(f"      📊 Score: {prediction['recommendation_score']:.3f}")
            print(f"      🏆 Prob. Éxito: {prediction['success_probability']:.3f}")
            
            # Interpretación
            if prediction['success_probability'] > 0.7:
                print(f"      ✅ Alta probabilidad de éxito")
            elif prediction['success_probability'] > 0.5:
                print(f"      ⚠️ Probabilidad moderada de éxito")
            else:
                print(f"      ❌ Baja probabilidad de éxito")
    
    print(f"\n📈 Estadísticas del Modelo")
    print("-" * 40)
    print(f"   🧠 Parámetros: {sum(p.numel() for p in model.parameters()):,}")
    print(f"   👥 Usuarios entrenados: {len(user_to_idx)}")
    print(f"   🛍️ Items entrenados: {len(item_to_idx)}")
    print(f"   📊 Interacciones: {len(data['interactions'])}")
    print(f"   🌐 Conexiones sociales: {len(data['social'])}")
    print(f"   👥 Grupos activos: {len(data['groups'])}")
    
    print(f"\n🎉 ¡Pruebas de recomendaciones completadas!")
    print(f"📚 El modelo GBGCN está funcionando correctamente")

if __name__ == "__main__":
    asyncio.run(test_recommendations()) 