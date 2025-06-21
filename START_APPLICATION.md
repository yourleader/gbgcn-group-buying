# 🚀 Cómo Ejecutar la Aplicación Group Buying GBGCN

## ✅ Sistema Completamente Funcional

El sistema Group Buying basado en GBGCN está **100% implementado y funcionando**.

---

## 🔧 Requisitos Previos

- ✅ **Python 3.12** instalado
- ✅ **PostgreSQL** ejecutándose en localhost:5432
  - Usuario: `postgres`
  - Password: `postgres`
  - Base de datos: `groupbuy_db` (se crea automáticamente)

---

## 🚀 Inicio Rápido

### 1. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 2. Configurar Variables de Entorno
El archivo `.env` ya está configurado correctamente para PostgreSQL.

### 3. Ejecutar la Aplicación
```bash
# Configurar PYTHONPATH y ejecutar
$env:PYTHONPATH = "."; python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Verificar que Funciona
- **API**: http://localhost:8000
- **Documentación**: http://localhost:8000/docs
- **API Base**: http://localhost:8000/api/v1

---

## 🧪 Probar la API

```bash
# Ejecutar script de pruebas
python test_api.py
```

---

## 📊 Estado Actual

✅ **PostgreSQL** conectado y funcionando
✅ **Base de datos** creada con todas las tablas GBGCN
✅ **API FastAPI** ejecutándose en puerto 8000
✅ **Autenticación JWT** implementada
✅ **Endpoints principales** funcionando
✅ **Modelo GBGCN** implementado con PyTorch
✅ **Recomendaciones IA** disponibles

---

## 📱 Para Flutter Developers

### Base URL para Flutter App
```dart
const String baseUrl = 'http://localhost:8000/api/v1';
```

### Endpoints Principales
- `POST /auth/register` - Registro
- `POST /auth/login` - Login
- `GET /users/me` - Perfil usuario
- `GET /items` - Listar productos
- `POST /groups` - Crear grupo de compra
- `GET /recommendations/items` - Recomendaciones IA
- `GET /recommendations/groups` - Grupos recomendados

### Documentación Completa
📖 **Ver**: `API_DOCUMENTATION.md` para detalles completos

---

## 🎯 Características GBGCN Implementadas

- **Multi-view Embedding**: Vistas iniciador vs participante
- **Cross-view Propagation**: Intercambio de información
- **Social Influence Modeling**: Análisis de redes sociales
- **Group Success Prediction**: Predicción de éxito con IA
- **Real-time Recommendations**: Recomendaciones en tiempo real
- **Graph Neural Networks**: Procesamiento de grafos heterogéneos

---

## 🔗 URLs Importantes

- **API**: http://localhost:8000/api/v1
- **Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

*🎉 ¡Sistema completamente funcional y listo para integración con Flutter!* 