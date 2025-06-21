#!/usr/bin/env python3
"""
Script simple para entrenar el modelo GBGCN
"""
import sys
import torch
import torch.nn as nn
import numpy as np
from pathlib import Path
import asyncio
import asyncpg

# Agregar src al path
sys.path.append(str(Path(__file__).parent.parent / "src"))

async def load_simple_data():
    """Cargar datos básicos para entrenamiento"""
    print("📊 Cargando datos para entrenamiento GBGCN...")
    
    conn = await asyncpg.connect(
        user="postgres",
        password="postgres",
        database="groupbuy_db",
        host="localhost",
        port=5432
    )
    
    try:
        # Cargar usuarios y crear mapeo
        users = await conn.fetch("SELECT id FROM users")
        user_ids = [r['id'] for r in users]
        user_to_idx = {uid: idx for idx, uid in enumerate(user_ids)}
        
        # Cargar items y crear mapeo
        items = await conn.fetch("SELECT id FROM items")
        item_ids = [r['id'] for r in items]
        item_to_idx = {iid: idx for idx, iid in enumerate(item_ids)}
        
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
        
        print(f"   ✅ {len(users)} usuarios")
        print(f"   ✅ {len(items)} items")
        print(f"   ✅ {len(interactions)} interacciones")
        print(f"   ✅ {len(social)} conexiones sociales")
        
        return {
            'user_to_idx': user_to_idx,
            'item_to_idx': item_to_idx,
            'users': user_ids,
            'items': item_ids,
            'interactions': interactions,
            'social': social
        }
        
    finally:
        await conn.close()

def create_simple_model(num_users, num_items):
    """Crear un modelo GBGCN simplificado"""
    from ml.gbgcn_model import GBGCN
    
    model = GBGCN(
        num_users=num_users,
        num_items=num_items,
        embedding_dim=32,  # Más pequeño para empezar
        num_layers=2,
        dropout=0.1,
        alpha=0.6,
        beta=0.4
    )
    
    return model

def prepare_training_data(data):
    """Preparar datos de entrenamiento simples"""
    user_to_idx = data['user_to_idx']
    item_to_idx = data['item_to_idx']
    
    # Crear edges para las vistas
    initiator_edges = []
    participant_edges = []
    
    for interaction in data['interactions']:
        user_id = interaction['user_id']
        item_id = interaction['item_id']
        
        if user_id in user_to_idx and item_id in item_to_idx:
            user_idx = user_to_idx[user_id]
            item_idx = item_to_idx[item_id]
            
            # Simular que algunos son iniciadores y otros participantes
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
    
    print(f"   📊 {len(initiator_edges)} edges iniciador")
    print(f"   📊 {len(participant_edges)} edges participante")
    print(f"   📊 {len(social_edges)} edges sociales")
    
    return {
        'initiator_edge_index': initiator_edge_index,
        'participant_edge_index': participant_edge_index,
        'social_edge_index': social_edge_index,
        'social_edge_weights': social_edge_weights
    }

async def simple_train():
    """Entrenamiento simple del modelo GBGCN"""
    print("🚀 Entrenamiento Simple GBGCN")
    print("=" * 40)
    
    # Cargar datos
    data = await load_simple_data()
    
    num_users = len(data['users'])
    num_items = len(data['items'])
    
    print(f"🔢 Configuración:")
    print(f"   👥 Usuarios: {num_users}")
    print(f"   🛍️ Items: {num_items}")
    
    # Crear modelo
    model = create_simple_model(num_users, num_items)
    print(f"🎯 Modelo creado con {sum(p.numel() for p in model.parameters())} parámetros")
    
    # Preparar datos
    training_data = prepare_training_data(data)
    
    # Configurar optimizador
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    # Entrenamiento simple
    model.train()
    num_epochs = 5
    
    print("🏋️ Iniciando entrenamiento...")
    
    for epoch in range(num_epochs):
        optimizer.zero_grad()
        
        # Crear batch de usuarios e items aleatorios
        batch_size = min(16, num_users, num_items)
        user_batch = torch.randint(0, num_users, (batch_size,))
        item_batch = torch.randint(0, num_items, (batch_size,))
        
        try:
            # Forward pass
            outputs = model(
                user_ids=user_batch,
                item_ids=item_batch,
                initiator_edge_index=training_data['initiator_edge_index'],
                participant_edge_index=training_data['participant_edge_index'],
                social_edge_index=training_data['social_edge_index'],
                social_edge_weights=training_data['social_edge_weights']
            )
            
            # Crear targets dummy para el ejemplo
            targets = torch.rand(batch_size)
            
            # Calcular loss simple
            loss = nn.MSELoss()(outputs['recommendation_score'], targets)
            
            # Backward pass
            loss.backward()
            optimizer.step()
            
            print(f"   Época {epoch+1}/{num_epochs} - Loss: {loss.item():.4f}")
            
        except Exception as e:
            print(f"   ⚠️ Error en época {epoch+1}: {e}")
            # Continuar con la siguiente época
            continue
    
    print("✅ Entrenamiento completado!")
    
    # Guardar modelo
    model_path = Path("models")
    model_path.mkdir(exist_ok=True)
    
    torch.save({
        'model_state_dict': model.state_dict(),
        'user_to_idx': data['user_to_idx'],
        'item_to_idx': data['item_to_idx'],
        'num_users': num_users,
        'num_items': num_items
    }, model_path / "gbgcn_simple.pth")
    
    print(f"💾 Modelo guardado en: {model_path / 'gbgcn_simple.pth'}")
    
    # Probar predicciones
    print("\n🧪 Probando predicciones...")
    model.eval()
    
    with torch.no_grad():
        # Probar con los primeros usuarios e items
        test_users = torch.tensor([0, 1, 2])
        test_items = torch.tensor([0, 1, 2])
        
        try:
            test_outputs = model(
                user_ids=test_users,
                item_ids=test_items,
                initiator_edge_index=training_data['initiator_edge_index'],
                participant_edge_index=training_data['participant_edge_index'],
                social_edge_index=training_data['social_edge_index'],
                social_edge_weights=training_data['social_edge_weights']
            )
            
            scores = test_outputs['recommendation_score']
            success_probs = test_outputs['success_probability']
            
            print(f"   📊 Scores de recomendación: {scores.numpy()}")
            print(f"   📊 Probabilidades de éxito: {success_probs.numpy()}")
            
        except Exception as e:
            print(f"   ⚠️ Error en predicciones: {e}")
    
    return model

if __name__ == "__main__":
    asyncio.run(simple_train()) 