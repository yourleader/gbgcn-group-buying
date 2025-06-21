# Group Buying API - GBGCN Implementation

## 📋 Descripción

Sistema de compras grupales basado en el paper **"Group-Buying Recommendation for Social E-Commerce"** que implementa el modelo **GBGCN (Group-Buying Graph Convolutional Network)**.

### 🔬 Características del Paper Implementadas

- **Multi-view Embedding Propagation**: Vista de iniciador vs participante
- **Cross-view Propagation**: Intercambio de información entre vistas
- **Social Influence Modeling**: Análisis de redes sociales
- **Heterogeneous Graph Neural Networks**: Grafos con usuarios, items e interacciones
- **Group Formation Optimization**: Optimización de formación de grupos
- **Success Probability Prediction**: Predicción de éxito de grupos

### 🏗️ Arquitectura del Sistema

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   GBGCN Model   │    │  PostgreSQL     │
│   REST API      │◄──►│   (PyTorch)     │◄──►│  Database       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Redis Cache   │    │  Graph Builder  │    │   Celery        │
│   & Sessions    │    │  (Heterogeneous)│    │   Workers       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Pasos de Implementación

### Paso 1: Preparación del Entorno

```bash
# Clonar el repositorio
git clone <repository-url>
cd groupbuy

# Crear archivo de variables de entorno
cp .env.example .env

# Editar variables de entorno según tu configuración
nano .env
```

### Paso 2: Configuración de Base de Datos

Crear archivo `.env` con las siguientes variables:

```env
# Database
DATABASE_URL=postgresql://groupbuy:password@localhost:5432/groupbuy_db

# GBGCN Model Parameters (del paper)
EMBEDDING_DIM=64
NUM_GCN_LAYERS=3
ALPHA=0.6
BETA=0.4
DROPOUT_RATE=0.1

# Security
SECRET_KEY=your-super-secret-key-change-in-production
```

### Paso 3: Instalación con Docker (Recomendado)

```bash
# Construir y ejecutar todos los servicios
docker-compose up --build

# Para ejecutar en background
docker-compose up -d

# Ver logs
docker-compose logs -f api
```

### Paso 4: Instalación Manual (Opcional)

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar base de datos
# Asegurar que PostgreSQL esté ejecutándose
createdb groupbuy_db

# Ejecutar migraciones
alembic upgrade head

# Iniciar el servidor
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Paso 5: Verificación del Sistema

```bash
# Verificar estado del API
curl http://localhost:8000/health

# Verificar estado del modelo GBGCN
curl http://localhost:8000/model/status

# Acceder a documentación interactiva
# Navegador: http://localhost:8000/docs
```

## 🧪 Uso del Sistema

### 1. Registro y Autenticación

```python
import requests

# Registro de usuario
response = requests.post("http://localhost:8000/api/v1/auth/register", json={
    "email": "usuario@example.com",
    "username": "usuario1",
    "password": "password123",
    "first_name": "Juan",
    "last_name": "Pérez"
})

# Login
response = requests.post("http://localhost:8000/api/v1/auth/login", json={
    "email": "usuario@example.com",
    "password": "password123"
})
token = response.json()["access_token"]
```

### 2. Recomendaciones GBGCN

```python
# Headers con token de autenticación
headers = {"Authorization": f"Bearer {token}"}

# Obtener recomendaciones para iniciar grupos
response = requests.post(
    "http://localhost:8000/api/v1/recommendations/recommend/items",
    json={
        "user_id": "user_id_here",
        "recommendation_type": "initiate",
        "limit": 10,
        "include_social_influence": True,
        "min_success_probability": 0.3
    },
    headers=headers
)
recommendations = response.json()
```

### 3. Análisis de Formación de Grupos

```python
# Analizar potencial de formación de grupo
response = requests.post(
    "http://localhost:8000/api/v1/recommendations/analyze/group-formation",
    json={
        "item_id": "item_id_here",
        "potential_participants": ["user1", "user2", "user3"],
        "target_quantity": 10,
        "max_participants": 20
    },
    headers=headers
)
analysis = response.json()
```

### 4. Red Social y Influencia

```python
# Obtener análisis de influencia social
response = requests.get(
    f"http://localhost:8000/api/v1/recommendations/social-influence/{user_id}",
    params={"item_id": "optional_item_id"},
    headers=headers
)
social_influence = response.json()
```

## 🔬 Algoritmos GBGCN Implementados

### 1. Multi-view Embedding Propagation

El sistema implementa las dos vistas del paper:

- **Vista Iniciador**: Para usuarios que crean grupos
- **Vista Participante**: Para usuarios que se unen a grupos

```python
# En src/ml/gbgcn_model.py
class GBGCN(nn.Module):
    def forward(self, user_ids, item_ids, initiator_edge_index, participant_edge_index):
        # Propagación en vista iniciador
        initiator_user_emb = all_user_emb
        for layer in self.initiator_gcn_layers:
            initiator_user_emb = layer(initiator_user_emb, initiator_edge_index)
        
        # Propagación en vista participante
        participant_user_emb = all_user_emb
        for layer in self.participant_gcn_layers:
            participant_user_emb = layer(participant_user_emb, participant_edge_index)
```

### 2. Social Influence Modeling

Implementa el modelado de influencia social del paper:

```python
class SocialInfluenceModule(nn.Module):
    def forward(self, user_embeddings, social_edge_index, social_edge_weights):
        # Propagación multi-capa de influencia social
        social_emb = user_embeddings
        for layer in self.social_gcn_layers:
            social_emb = layer(social_emb, social_edge_index, social_edge_weights)
        return self.influence_aggregator(social_emb)
```

### 3. Group Success Prediction

El modelo predice la probabilidad de éxito de grupos:

```python
# Combinación de embeddings multi-vista
combined_user_emb = (
    self.alpha * user_init_emb + 
    (1 - self.alpha) * user_part_emb + 
    self.beta * user_social_emb
)

# Predicción de éxito del grupo
success_probability = self.group_success_predictor(combined_features)
```

## 📊 Endpoints Principales

### Recomendaciones

- `POST /api/v1/recommendations/recommend/items` - Recomendaciones de items
- `POST /api/v1/recommendations/recommend/groups` - Recomendaciones de grupos
- `POST /api/v1/recommendations/analyze/group-formation` - Análisis de formación
- `POST /api/v1/recommendations/optimize/group-composition` - Optimización

### Usuarios y Social

- `POST /api/v1/auth/register` - Registro
- `POST /api/v1/auth/login` - Login
- `GET /api/v1/social/friends` - Lista de amigos
- `POST /api/v1/social/connect` - Conectar con amigos

### Grupos

- `POST /api/v1/groups/create` - Crear grupo
- `POST /api/v1/groups/{group_id}/join` - Unirse a grupo
- `GET /api/v1/groups/active` - Grupos activos

## 🧮 Parámetros del Modelo GBGCN

### Configuración por Defecto (del Paper)

```env
EMBEDDING_DIM=64          # Dimensión de embeddings
NUM_GCN_LAYERS=3          # Capas de GCN
ALPHA=0.6                 # Coeficiente iniciador vs participante
BETA=0.4                  # Coeficiente influencia social vs preferencia
DROPOUT_RATE=0.1          # Tasa de dropout
LEARNING_RATE=0.001       # Tasa de aprendizaje
BATCH_SIZE=512            # Tamaño de batch
```

### Optimización de Hiperparámetros

Para optimizar los parámetros según tu dataset:

```python
# En notebooks/hyperparameter_tuning.ipynb
hyperparameters = {
    'embedding_dim': [32, 64, 128],
    'num_layers': [2, 3, 4],
    'alpha': [0.4, 0.5, 0.6, 0.7],
    'beta': [0.3, 0.4, 0.5],
    'learning_rate': [0.0001, 0.001, 0.01]
}
```

## 📈 Monitoreo y Métricas

### Métricas del Paper Implementadas

- **Recall@K**: Precisión en recomendaciones top-K
- **NDCG@K**: Normalized Discounted Cumulative Gain
- **Success Rate**: Tasa de éxito de grupos formados

```python
# Ver métricas del modelo
response = requests.get("http://localhost:8000/model/status")
metrics = response.json()["metrics"]
```

## 🔧 Desarrollo y Contribución

### Estructura del Proyecto

```
groupbuy/
├── src/
│   ├── api/                 # FastAPI endpoints
│   ├── ml/                  # Modelo GBGCN
│   ├── database/            # Modelos SQLAlchemy
│   ├── services/            # Lógica de negocio
│   └── core/                # Configuración
├── notebooks/               # Jupyter notebooks
├── tests/                   # Pruebas unitarias
├── docker-compose.yml       # Configuración Docker
└── requirements.txt         # Dependencias
```

### Ejecutar Pruebas

```bash
# Ejecutar todas las pruebas
pytest

# Ejecutar pruebas específicas
pytest tests/test_gbgcn_model.py

# Con cobertura
pytest --cov=src tests/
```

### Jupyter Notebooks

```bash
# Acceder a Jupyter (si se ejecuta con Docker)
# Navegador: http://localhost:8888

# Notebooks disponibles:
# - gbgcn_analysis.ipynb: Análisis del modelo
# - data_exploration.ipynb: Exploración de datos
# - hyperparameter_tuning.ipynb: Optimización
```

## 📚 Referencias

- **Paper Original**: "Group-Buying Recommendation for Social E-Commerce"
- **PyTorch Geometric**: https://pytorch-geometric.readthedocs.io/
- **FastAPI**: https://fastapi.tiangolo.com/
- **SQLAlchemy**: https://sqlalchemy.org/

## 🤝 Soporte

Para soporte técnico o preguntas sobre la implementación:

1. Revisar la documentación en `/docs`
2. Verificar logs: `docker-compose logs api`
3. Consultar issues en el repositorio

## 📄 Licencia

Este proyecto implementa algoritmos del paper académico para fines educativos y de investigación. 