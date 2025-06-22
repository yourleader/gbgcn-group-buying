# 🧪 Guía de Pruebas del Modelo GBGCN

## 🎯 Resumen Rápido

El sistema Group Buying basado en GBGCN está **completamente implementado** y listo para probar. Tienes 3 formas de probarlo:

### ⚡ Opción 1: Prueba Ultra-Rápida (1 minuto)
```bash
# En PowerShell (Windows)
.\test_gbgcn.ps1

# En terminal (Linux/Mac)
python quick_test.py
```

### 🧪 Opción 2: Prueba Completa (3 minutos)
```bash
python test_gbgcn_complete.py
```

### 🔧 Opción 3: Manual
```bash
# Configurar entorno
$env:PYTHONPATH = "."

# Iniciar servidor
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🔑 Credenciales y Tokens

### Para la API:
- **Base URL**: `http://localhost:8000/api/v1`
- **Documentación**: `http://localhost:8000/docs`

### Usuario de Prueba:
- **Email**: `gbgcn@test.com`
- **Password**: `test123456`
- **Username**: `gbgcn_tester`

### Para obtener Token:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "gbgcn@test.com", "password": "test123456"}'
```

**Respuesta:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

## 🛠️ Endpoints del Modelo GBGCN

### Autenticación
- `POST /auth/register` - Registro de usuario
- `POST /auth/login` - Login y obtener token

### Recomendaciones GBGCN (Requieren token)
- `GET /recommendations/items` - Recomendaciones personalizadas
- `GET /recommendations/groups` - Grupos recomendados
- `POST /recommendations/predict-success` - Predicción de éxito
- `GET /recommendations/social-influence` - Análisis de influencia social

### Gestión de Datos
- `POST /items` - Crear productos
- `GET /items` - Listar productos
- `POST /groups` - Crear grupos de compra
- `GET /groups` - Listar grupos

---

## 🤖 Probar el Modelo GBGCN

### 1. Obtener Recomendaciones
```bash
curl -X GET "http://localhost:8000/api/v1/recommendations/items" \
  -H "Authorization: Bearer TU_TOKEN_AQUI"
```

### 2. Predicción de Éxito de Grupo
```bash
curl -X POST "http://localhost:8000/api/v1/recommendations/predict-success" \
  -H "Authorization: Bearer TU_TOKEN_AQUI" \
  -H "Content-Type: application/json" \
  -d '{
    "item_id": 1,
    "target_quantity": 10,
    "duration_days": 7
  }'
```

### 3. Análisis de Influencia Social
```bash
curl -X GET "http://localhost:8000/api/v1/recommendations/social-influence" \
  -H "Authorization: Bearer TU_TOKEN_AQUI"
```

---

## 📱 Para Desarrolladores Flutter

### Configuración Dart
```dart
class ApiConfig {
  static const String baseUrl = 'http://localhost:8000/api/v1';
  static const String loginEndpoint = '/auth/login';
  static const String recommendationsEndpoint = '/recommendations/items';
}
```

### Ejemplo de Login
```dart
Future<String?> login(String email, String password) async {
  final response = await http.post(
    Uri.parse('${ApiConfig.baseUrl}/auth/login'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({
      'email': email,
      'password': password,
    }),
  );
  
  if (response.statusCode == 200) {
    final data = jsonDecode(response.body);
    return data['access_token'];
  }
  return null;
}
```

### Ejemplo de Recomendaciones
```dart
Future<List<dynamic>> getRecommendations(String token) async {
  final response = await http.get(
    Uri.parse('${ApiConfig.baseUrl}/recommendations/items'),
    headers: {
      'Authorization': 'Bearer $token',
      'Content-Type': 'application/json',
    },
  );
  
  if (response.statusCode == 200) {
    return jsonDecode(response.body);
  }
  return [];
}
```

---

## 🔍 Características del Modelo GBGCN

### Algoritmos Implementados:
- ✅ **Multi-view Embedding**: Vistas iniciador vs participante
- ✅ **Cross-view Attention**: Atención cruzada entre vistas
- ✅ **Social Influence Modeling**: Análisis de redes sociales
- ✅ **Graph Convolutional Networks**: GCN heterogéneos
- ✅ **Success Prediction**: Predicción de éxito de grupos
- ✅ **Real-time Recommendations**: Recomendaciones en tiempo real

### Parámetros del Paper:
- **ALPHA**: 0.6 (peso vista iniciador)
- **BETA**: 0.4 (peso influencia social)
- **EMBEDDING_DIM**: 64
- **NUM_LAYERS**: 3
- **DROPOUT**: 0.1

---

## 🚨 Solución de Problemas

### Error: "ModuleNotFoundError"
```bash
pip install -r requirements.txt
```

### Error: "Connection refused"
```bash
# Verificar que el servidor esté corriendo
curl http://localhost:8000/health
```

### Error: "Database connection"
```bash
# El sistema usa SQLite automáticamente
# No necesitas PostgreSQL para las pruebas
```

### Error: "Token expired"
```bash
# Obtén un nuevo token haciendo login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "gbgcn@test.com", "password": "test123456"}'
```

---

## 📊 Resultados Esperados

### Recomendaciones de Items:
```json
[
  {
    "id": 1,
    "name": "iPhone 15 Pro",
    "base_price": 999.99,
    "recommendation_score": 0.847,
    "success_probability": 0.732
  }
]
```

### Predicción de Éxito:
```json
{
  "success_probability": 0.762,
  "recommendation_score": 0.834,
  "estimated_participants": 8,
  "completion_time_days": 4.2
}
```

---

## 🎉 Estado del Sistema

- ✅ **Modelo GBGCN**: Completamente implementado
- ✅ **API REST**: 30+ endpoints funcionando
- ✅ **Base de Datos**: SQLite/PostgreSQL soportados
- ✅ **Autenticación**: JWT tokens
- ✅ **Recomendaciones**: IA funcionando
- ✅ **Documentación**: Swagger UI disponible

---

## 📞 Soporte

Si tienes problemas:
1. Ejecuta `python test_gbgcn_complete.py` para diagnóstico completo
2. Revisa `http://localhost:8000/docs` para documentación interactiva
3. Verifica que todas las dependencias estén instaladas

**¡El sistema está listo para integración con Flutter!** 🚀 