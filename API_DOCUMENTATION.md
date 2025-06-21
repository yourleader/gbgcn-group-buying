# API Group Buying GBGCN - Documentación para Flutter

## 🚀 Sistema Completamente Funcional

**Base URL**: `http://localhost:8000/api/v1`
**Documentación Swagger**: `http://localhost:8000/docs`

---

## 📊 Estado del Sistema

✅ **PostgreSQL configurado** (usuario: postgres, password: postgres)
✅ **Base de datos creada** con todas las tablas del modelo GBGCN
✅ **API FastAPI ejecutándose** en puerto 8000
✅ **Autenticación JWT funcional**
✅ **Endpoints principales implementados**

---

## 🔐 Autenticación

### Registro de Usuario
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "username": "usuario123",
  "email": "usuario@example.com",
  "password": "password123",
  "first_name": "Nombre",
  "last_name": "Apellido",
  "phone": "+1234567890"
}
```

**Respuesta 201:**
```json
{
  "id": "user_id",
  "username": "usuario123",
  "email": "usuario@example.com",
  "first_name": "Nombre",
  "last_name": "Apellido",
  "is_verified": false,
  "is_active": true,
  "reputation_score": 0.0,
  "created_at": "2025-06-20T17:00:00Z"
}
```

### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "usuario@example.com",
  "password": "password123"
}
```

**Respuesta 200:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

## 👤 Gestión de Usuarios

### Obtener Perfil Actual
```http
GET /api/v1/users/me
Authorization: Bearer {access_token}
```

### Actualizar Perfil
```http
PUT /api/v1/users/me
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "first_name": "Nuevo Nombre",
  "last_name": "Nuevo Apellido",
  "phone": "+0987654321"
}
```

### Buscar Usuarios
```http
GET /api/v1/users/search?q=nombre&limit=10
Authorization: Bearer {access_token}
```

---

## 🛍️ Gestión de Items

### Crear Item
```http
POST /api/v1/items
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "iPhone 15 Pro",
  "description": "Latest iPhone with advanced features",
  "base_price": 999.99,
  "category_id": "category_id",
  "min_group_size": 5,
  "max_group_size": 50,
  "images": ["url1.jpg", "url2.jpg"],
  "specifications": {
    "color": "Natural Titanium",
    "storage": "256GB"
  }
}
```

### Listar Items
```http
GET /api/v1/items?limit=20&offset=0&category_id=category_id
Authorization: Bearer {access_token}
```

### Obtener Item por ID
```http
GET /api/v1/items/{item_id}
Authorization: Bearer {access_token}
```

---

## 👥 Gestión de Grupos

### Crear Grupo de Compra
```http
POST /api/v1/groups
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "title": "iPhone 15 Pro Group Buy",
  "description": "Let's buy iPhone 15 Pro together for better price",
  "item_id": "item_id",
  "target_quantity": 10,
  "min_participants": 5,
  "end_date": "2025-07-01T00:00:00Z",
  "delivery_address": "123 Main St, City"
}
```

### Listar Grupos
```http
GET /api/v1/groups?status=active&limit=20&offset=0
Authorization: Bearer {access_token}
```

### Unirse a Grupo
```http
POST /api/v1/groups/{group_id}/join
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "quantity": 2
}
```

### Abandonar Grupo
```http
DELETE /api/v1/groups/{group_id}/leave
Authorization: Bearer {access_token}
```

---

## 🤖 Recomendaciones GBGCN (IA)

### Recomendaciones de Items
```http
GET /api/v1/recommendations/items?limit=10
Authorization: Bearer {access_token}
```

**Respuesta:**
```json
{
  "recommendations": [
    {
      "item_id": "item_123",
      "item_name": "iPhone 15 Pro",
      "recommendation_score": 0.95,
      "success_probability": 0.88,
      "predicted_price": 899.99,
      "reasoning": "High social influence from your network"
    }
  ],
  "model_version": "gbgcn_v1.0",
  "generated_at": "2025-06-20T17:00:00Z"
}
```

### Recomendaciones de Grupos
```http
GET /api/v1/recommendations/groups?limit=10
Authorization: Bearer {access_token}
```

### Predicción de Éxito de Grupo
```http
POST /api/v1/recommendations/predict-success
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "group_composition": ["user1", "user2", "user3"],
  "item_id": "item_123",
  "target_quantity": 10
}
```

### Análisis de Influencia Social
```http
GET /api/v1/recommendations/social-influence
Authorization: Bearer {access_token}
```

### Optimización de Composición de Grupo
```http
POST /api/v1/recommendations/optimize-group-composition
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "item_id": "item_123",
  "target_size": 10,
  "current_members": ["user1", "user2"]
}
```

---

## 📊 Analytics y Reportes

### Estadísticas de Usuario
```http
GET /api/v1/analytics/user-stats
Authorization: Bearer {access_token}
```

### Métricas de Grupo
```http
GET /api/v1/analytics/group-metrics?group_id=group_123
Authorization: Bearer {access_token}
```

### Análisis de Rendimiento del Modelo
```http
GET /api/v1/analytics/model-performance
Authorization: Bearer {access_token}
```

---

## 🌐 Red Social

### Añadir Conexión Social
```http
POST /api/v1/social/connections
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "friend_id": "user_456",
  "connection_type": "friend"
}
```

### Obtener Conexiones
```http
GET /api/v1/social/connections?limit=50
Authorization: Bearer {access_token}
```

### Análisis de Influencia
```http
GET /api/v1/social/influence-analysis?user_id=user_123
Authorization: Bearer {access_token}
```

---

## 🔧 Códigos de Estado HTTP

- **200**: Éxito
- **201**: Creado exitosamente
- **400**: Error en la solicitud (datos inválidos)
- **401**: No autorizado (token inválido/expirado)
- **403**: Prohibido (sin permisos)
- **404**: No encontrado
- **422**: Error de validación
- **500**: Error interno del servidor

---

## 🚀 Configuración para Flutter

### 1. Base URL Configuration
```dart
class ApiConfig {
  static const String baseUrl = 'http://localhost:8000/api/v1';
  static const String docsUrl = 'http://localhost:8000/docs';
}
```

### 2. HTTP Client con Autenticación
```dart
class ApiClient {
  final String baseUrl;
  late final Dio _dio;
  
  ApiClient({required this.baseUrl}) {
    _dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: Duration(seconds: 5),
      receiveTimeout: Duration(seconds: 30),
    ));
    
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) {
        final token = getStoredToken();
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
    ));
  }
}
```

### 3. Modelos de Datos
```dart
class User {
  final String id;
  final String username;
  final String email;
  final String firstName;
  final String lastName;
  final bool isVerified;
  final double reputationScore;
  
  User.fromJson(Map<String, dynamic> json)
    : id = json['id'],
      username = json['username'],
      email = json['email'],
      firstName = json['first_name'],
      lastName = json['last_name'],
      isVerified = json['is_verified'],
      reputationScore = json['reputation_score']?.toDouble() ?? 0.0;
}

class GroupBuyItem {
  final String id;
  final String name;
  final String description;
  final double basePrice;
  final int minGroupSize;
  final int maxGroupSize;
  final List<String> images;
  
  GroupBuyItem.fromJson(Map<String, dynamic> json)
    : id = json['id'],
      name = json['name'],
      description = json['description'],
      basePrice = json['base_price']?.toDouble() ?? 0.0,
      minGroupSize = json['min_group_size'],
      maxGroupSize = json['max_group_size'],
      images = List<String>.from(json['images'] ?? []);
}
```

---

## 🎯 Características Implementadas del Paper GBGCN

✅ **Multi-view Embedding Propagation**: Vistas separadas para iniciadores vs participantes
✅ **Cross-view Propagation**: Intercambio de información entre vistas 
✅ **Social Influence Modeling**: Análisis de redes sociales con GCN
✅ **Group Success Prediction**: Predicción de probabilidad de éxito
✅ **Heterogeneous Graph Neural Networks**: Procesamiento de grafos usuario-item-grupo
✅ **Real-time Recommendations**: API endpoints para recomendaciones en tiempo real
✅ **Social Network Analysis**: Análisis de influencia y conexiones sociales
✅ **Group Formation Optimization**: Optimización de composición de grupos

---

## 📱 Próximos Pasos para Flutter

1. **Configurar HTTP Client** con interceptores para autenticación
2. **Implementar Authentication Flow** (login, registro, refresh tokens)
3. **Crear Models** para usuarios, items, grupos y recomendaciones
4. **Implementar State Management** (Provider, Riverpod, o Bloc)
5. **Diseñar UI** para explorar items, crear/unirse a grupos
6. **Integrar recomendaciones GBGCN** en la interfaz
7. **Implementar notificaciones** para updates de grupos

---

## 🔗 URLs Importantes

- **API Base**: `http://localhost:8000/api/v1`
- **Documentación Swagger**: `http://localhost:8000/docs`
- **Documentación ReDoc**: `http://localhost:8000/redoc`

---

*Sistema Group Buying basado en GBGCN - Completamente funcional y listo para integración con Flutter* 🚀 