#!/usr/bin/env python3
"""
Script para entrenar el modelo GBGCN con datos de ejemplo
"""
import sys
import os
import torch
import torch.nn.functional as F
import numpy as np
from pathlib import Path
import asyncio
import asyncpg
import json
from datetime import datetime

# Agregar src al path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from ml.gbgcn_model import GBGCN, create_heterogeneous_graph
from ml.gbgcn_trainer import GBGCNTrainer
from core.config import settings

async def load_training_data():
    """Cargar datos de entrenamiento desde PostgreSQL"""
    print("📊 Cargando datos de entrenamiento...")
    
    conn = await asyncpg.connect(
        user="postgres",
        password="postgres",
        database="groupbuy_db",
        host="localhost",
        port=5432
    )
    
    try:
        # Cargar usuarios
        users_data = await conn.fetch("SELECT id, reputation_score, success_rate FROM users")
        print(f"   ✅ {len(users_data)} usuarios cargados")
        
        # Cargar items
        items_data = await conn.fetch("SELECT id, base_price, min_group_size, max_group_size FROM items")
        print(f"   ✅ {len(items_data)} items cargados")
        
        # Cargar grupos
        groups_data = await conn.fetch("""
            SELECT id, item_id, creator_id, target_quantity, current_quantity, 
                   success_probability, social_influence_score, status
            FROM groups
        """)
        print(f"   ✅ {len(groups_data)} grupos cargados")
        
        # Cargar interacciones
        interactions_data = await conn.fetch("""
            SELECT user_id, item_id, interaction_type, interaction_value, created_at
            FROM user_item_interactions
            ORDER BY created_at
        """)
        print(f"   ✅ {len(interactions_data)} interacciones cargadas")
        
        # Cargar conexiones sociales
        social_data = await conn.fetch("""
            SELECT user_id, friend_id, connection_strength, interaction_frequency
            FROM social_connections
        """)
        print(f"   ✅ {len(social_data)} conexiones sociales cargadas")
        
        return {
            'users': users_data,
            'items': items_data,
            'groups': groups_data,
            'interactions': interactions_data,
            'social': social_data
        }
        
    finally:
        await conn.close()

def create_mappings(data):
    """Crear mapeos de IDs a índices"""
    users = list(set([r['id'] for r in data['users']]))
    items = list(set([r['id'] for r in data['items']]))
    
    user_to_idx = {user_id: idx for idx, user_id in enumerate(users)}
    item_to_idx = {item_id: idx for idx, item_id in enumerate(items)}
    
    return user_to_idx, item_to_idx, users, items

def prepare_graph_data(data, user_to_idx, item_to_idx):
    """Preparar datos para crear el grafo heterogéneo"""
    print("🔧 Preparando datos del grafo...")
    
    # Preparar interacciones usuario-item
    user_item_edges = []
    interaction_features = []
    
    for interaction in data['interactions']:
        user_id = interaction['user_id']
        item_id = interaction['item_id']
        
        if user_id in user_to_idx and item_id in item_to_idx:
            user_idx = user_to_idx[user_id]
            item_idx = item_to_idx[item_id]
            
            user_item_edges.append([user_idx, item_idx])
            
            # Convertir tipo de interacción a valor numérico
            interaction_type_value = {
                'view': 0.2,
                'like': 0.5,
                'share': 0.7,
                'add_to_wishlist': 0.8,
                'join_group': 1.0
            }.get(interaction['interaction_type'], 0.1)
            
            interaction_features.append([
                interaction['interaction_value'] or 0.0,
                interaction_type_value
            ])
    
    # Preparar conexiones sociales
    social_edges = []
    social_features = []
    
    for connection in data['social']:
        user1_id = connection['user_id']
        user2_id = connection['friend_id']
        
        if user1_id in user_to_idx and user2_id in user_to_idx:
            user1_idx = user_to_idx[user1_id]
            user2_idx = user_to_idx[user2_id]
            
            social_edges.append([user1_idx, user2_idx])
            social_features.append([
                connection['connection_strength'] or 0.5,
                connection['interaction_frequency'] or 0.3
            ])
    
    # Preparar características de usuarios
    user_features = []
    for user_data in data['users']:
        user_features.append([
            user_data['reputation_score'] or 2.5,
            user_data['success_rate'] or 0.5
        ])
    
    # Preparar características de items
    item_features = []
    for item_data in data['items']:
        # Normalizar precio (dividir por 1000)
        normalized_price = (item_data['base_price'] or 100.0) / 1000.0
        item_features.append([
            normalized_price,
            float(item_data['min_group_size'] or 5),
            float(item_data['max_group_size'] or 50)
        ])
    
    # Preparar datos de grupos para entrenamiento
    group_targets = []
    group_compositions = []
    
    for group in data['groups']:
        # Solo usar grupos activos o completados para entrenamiento
        if group['status'] in ['active', 'completed']:
            success_label = 1 if group['status'] == 'completed' else 0
            group_targets.append(success_label)
            
            # Características del grupo
            creator_id = group['creator_id']
            item_id = group['item_id']
            
            if creator_id in user_to_idx and item_id in item_to_idx:
                group_compositions.append([
                    user_to_idx[creator_id],
                    item_to_idx[item_id],
                    float(group['target_quantity'] or 10),
                    float(group['current_quantity'] or 5),
                    group['success_probability'] or 0.5,
                    group['social_influence_score'] or 0.3
                ])
    
    print(f"   ✅ {len(user_item_edges)} interacciones usuario-item")
    print(f"   ✅ {len(social_edges)} conexiones sociales")
    print(f"   ✅ {len(user_features)} usuarios con características")
    print(f"   ✅ {len(item_features)} items con características")
    print(f"   ✅ {len(group_targets)} grupos para entrenamiento")
    
    return {
        'user_item_edges': torch.tensor(user_item_edges, dtype=torch.long).t(),
        'interaction_features': torch.tensor(interaction_features, dtype=torch.float32),
        'social_edges': torch.tensor(social_edges, dtype=torch.long).t(),
        'social_features': torch.tensor(social_features, dtype=torch.float32),
        'user_features': torch.tensor(user_features, dtype=torch.float32),
        'item_features': torch.tensor(item_features, dtype=torch.float32),
        'group_targets': torch.tensor(group_targets, dtype=torch.float32),
        'group_compositions': torch.tensor(group_compositions, dtype=torch.float32)
    }

async def train_model():
    """Entrenar el modelo GBGCN"""
    print("🚀 Iniciando entrenamiento del modelo GBGCN")
    print("=" * 50)
    
    # Cargar datos
    data = await load_training_data()
    
    # Crear mapeos
    user_to_idx, item_to_idx, users, items = create_mappings(data)
    
    # Preparar datos del grafo
    graph_data = prepare_graph_data(data, user_to_idx, item_to_idx)
    
    # Configurar dimensiones
    num_users = len(users)
    num_items = len(items)
    user_feature_dim = graph_data['user_features'].size(1)
    item_feature_dim = graph_data['item_features'].size(1)
    
    print(f"🔢 Configuración del modelo:")
    print(f"   👥 Usuarios: {num_users}")
    print(f"   🛍️ Items: {num_items}")
    print(f"   📊 Dim. características usuarios: {user_feature_dim}")
    print(f"   📊 Dim. características items: {item_feature_dim}")
    print(f"   🧠 Dim. embeddings: {settings.EMBEDDING_DIM}")
    
    # Crear el grafo heterogéneo
    # Convertir tensors de vuelta a listas de tuplas para la función
    user_item_interactions = []
    edge_array = graph_data['user_item_edges'].t().numpy()
    for i, (user_idx, item_idx) in enumerate(edge_array):
        interaction_type = 'join_group'  # Tipo por defecto
        user_item_interactions.append((int(user_idx), int(item_idx), interaction_type))
    
    social_connections = []
    if graph_data['social_edges'].size(0) > 0:
        social_edge_array = graph_data['social_edges'].t().numpy()
        social_weights = graph_data['social_features'][:, 0].numpy()
        for i, (user1_idx, user2_idx) in enumerate(social_edge_array):
            weight = float(social_weights[i]) if i < len(social_weights) else 0.5
            social_connections.append((int(user1_idx), int(user2_idx), weight))
    
    hetero_graph = create_heterogeneous_graph(
        user_item_interactions=user_item_interactions,
        social_connections=social_connections,
        num_users=num_users,
        num_items=num_items
    )
    
    # Crear el modelo
    model = GBGCN(
        num_users=num_users,
        num_items=num_items,
        embedding_dim=settings.EMBEDDING_DIM,
        num_layers=settings.NUM_GCN_LAYERS,
        dropout=settings.DROPOUT_RATE,
        alpha=settings.ALPHA,
        beta=settings.BETA
    )
    
    print(f"🎯 Modelo creado con {sum(p.numel() for p in model.parameters())} parámetros")
    
    # Configurar el entrenador
    trainer = GBGCNTrainer(
        model=model,
        learning_rate=settings.LEARNING_RATE,
        device='cpu'  # Usar CPU por ahora
    )
    
    # Simular datos de entrenamiento
    # En un caso real, esto vendría de datos históricos
    print("🎲 Generando datos de entrenamiento sintéticos...")
    
    # Crear batch de datos simulados
    batch_size = min(32, len(graph_data['group_targets']))
    if batch_size == 0:
        print("⚠️ No hay suficientes datos de grupos para entrenamiento")
        batch_size = 10
        # Crear datos sintéticos mínimos
        user_indices = torch.randint(0, num_users, (batch_size,))
        item_indices = torch.randint(0, num_items, (batch_size,))
        group_features = torch.randn(batch_size, 6)
        success_labels = torch.randint(0, 2, (batch_size,)).float()
    else:
        # Usar datos reales limitados al batch_size
        user_indices = graph_data['group_compositions'][:batch_size, 0].long()
        item_indices = graph_data['group_compositions'][:batch_size, 1].long()
        group_features = graph_data['group_compositions'][:batch_size, 2:]
        success_labels = graph_data['group_targets'][:batch_size]
    
    # Entrenar el modelo
    print("🏋️ Entrenando modelo...")
    
    # Simular épocas de entrenamiento
    num_epochs = 10  # Reducido para demo
    
    for epoch in range(num_epochs):
        # Paso de entrenamiento
        loss = trainer.train_step(
            hetero_graph=hetero_graph,
            user_features=graph_data['user_features'],
            item_features=graph_data['item_features'],
            user_indices=user_indices,
            item_indices=item_indices,
            group_features=group_features,
            success_labels=success_labels
        )
        
        if epoch % 2 == 0:
            print(f"   Época {epoch+1}/{num_epochs} - Loss: {loss:.4f}")
    
    print("✅ Entrenamiento completado!")
    
    # Guardar el modelo
    model_path = Path("models")
    model_path.mkdir(exist_ok=True)
    
    torch.save({
        'model_state_dict': model.state_dict(),
        'user_to_idx': user_to_idx,
        'item_to_idx': item_to_idx,
        'model_config': {
            'num_users': num_users,
            'num_items': num_items,
            'user_feature_dim': user_feature_dim,
            'item_feature_dim': item_feature_dim,
            'embedding_dim': settings.EMBEDDING_DIM,
            'hidden_dim': 128,
            'num_layers': settings.NUM_GCN_LAYERS,
            'dropout': settings.DROPOUT_RATE,
            'alpha': settings.ALPHA,
            'beta': settings.BETA
        }
    }, model_path / "gbgcn_model.pth")
    
    print(f"💾 Modelo guardado en: {model_path / 'gbgcn_model.pth'}")
    
    # Probar predicciones
    print("\n🧪 Probando predicciones...")
    model.eval()
    
    with torch.no_grad():
        # Generar embeddings
        user_embeddings_init, user_embeddings_part, item_embeddings = model.forward_embeddings(
            hetero_graph, graph_data['user_features'], graph_data['item_features']
        )
        
        # Probar predicción de éxito para un grupo de ejemplo
        if len(user_indices) > 0:
            sample_user = user_indices[0:1]
            sample_item = item_indices[0:1]
            sample_group_features = group_features[0:1]
            
            success_prob = model.predict_success(
                user_embeddings_init, user_embeddings_part, item_embeddings,
                sample_user, sample_item, sample_group_features
            )
            
            print(f"   📊 Probabilidad de éxito (ejemplo): {success_prob.item():.3f}")
    
    return model, user_to_idx, item_to_idx

if __name__ == "__main__":
    asyncio.run(train_model()) 