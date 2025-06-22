# 📱 FLUTTER + GBGCN MODEL - INTEGRATION GUIDE
**Guía completa para integrar el modelo GBGCN en tu app de Flutter**

## 🎯 **ARQUITECTURA DE INTEGRACIÓN**

### **1. FLUJO PRINCIPAL DE USUARIO**
```
🏠 Home Screen → 🧠 GBGCN Recommendations → 📦 Product Details → 👥 Group Buying → 💰 Checkout
```

### **2. PANTALLAS CLAVE CON GBGCN**

#### **📱 A. PANTALLA PRINCIPAL (Home)**
```dart
// Endpoints a usar:
GET /api/v1/recommendations/items  // Recomendaciones principales
GET /api/v1/groups/               // Grupos activos
GET /api/v1/analytics/dashboard   // Métricas del usuario
```

**UI Components:**
- **🔥 "Recomendaciones para ti"** (cards con score GBGCN)
- **⚡ "Grupos formándose"** (grupos con alta probabilidad de éxito)
- **📊 "Tu dashboard"** (métricas personalizadas)

#### **📱 B. PANTALLA DE RECOMENDACIONES**
```dart
class GBGCNRecommendationsScreen extends StatefulWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('🧠 Recomendaciones GBGCN')),
      body: Column(
        children: [
          // Filtros inteligentes
          _buildIntelligentFilters(),
          
          // Lista de recomendaciones con scores
          Expanded(
            child: ListView.builder(
              itemBuilder: (context, index) => _buildRecommendationCard(recommendations[index])
            )
          )
        ]
      )
    );
  }
  
  Widget _buildRecommendationCard(ItemRecommendation item) {
    return Card(
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: _getScoreColor(item.recommendationScore),
          child: Text('${(item.recommendationScore * 100).toInt()}')
        ),
        title: Text(item.title),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('💰 Precio estimado: \$${item.predictedPrice}'),
            Text('📊 Prob. éxito: ${(item.successProbability * 100).toInt()}%'),
            Text('🤝 Influencia social: ${(item.socialInfluenceScore * 100).toInt()}%'),
          ]
        ),
        trailing: ElevatedButton(
          onPressed: () => _createOrJoinGroup(item),
          child: Text(_getActionText(item))
        )
      )
    );
  }
}
```

#### **📱 C. PANTALLA DE DETALLES DE PRODUCTO**
```dart
// Integración GBGCN en detalles
class ProductDetailsScreen extends StatelessWidget {
  Widget build(BuildContext context) {
    return Scaffold(
      body: Column(
        children: [
          // Información del producto
          _buildProductInfo(),
          
          // 🧠 SECCIÓN GBGCN
          _buildGBGCNSection(),
          
          // Botones de acción
          _buildActionButtons()
        ]
      )
    );
  }
  
  Widget _buildGBGCNSection() {
    return Container(
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.blue.shade50,
        borderRadius: BorderRadius.circular(12)
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('🧠 Análisis GBGCN', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          SizedBox(height: 8),
          
          // Score de recomendación
          _buildScoreRow('🎯 Score recomendación', gbgcnData.recommendationScore),
          _buildScoreRow('📊 Probabilidad éxito', gbgcnData.successProbability),
          _buildScoreRow('🤝 Influencia social', gbgcnData.socialInfluence),
          
          SizedBox(height: 12),
          
          // Grupos sugeridos
          Text('👥 Grupos disponibles:', style: TextStyle(fontWeight: FontWeight.w600)),
          ...suggestedGroups.map((group) => _buildGroupSuggestion(group))
        ]
      )
    );
  }
}
```

#### **📱 D. PANTALLA DE CREACIÓN DE GRUPO**
```dart
class CreateGroupScreen extends StatefulWidget {
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('🚀 Crear Grupo')),
      body: Form(
        child: Column(
          children: [
            // Campos básicos
            _buildBasicFields(),
            
            // 🧠 PREDICCIONES GBGCN
            _buildGBGCNPredictions(),
            
            // Configuración inteligente
            _buildIntelligentConfiguration(),
            
            ElevatedButton(
              onPressed: _createGroupWithGBGCN,
              child: Text('🚀 Crear Grupo Inteligente')
            )
          ]
        )
      )
    );
  }
  
  Widget _buildGBGCNPredictions() {
    return FutureBuilder<GroupFormationAnalysis>(
      future: _analyzeGroupFormation(),
      builder: (context, snapshot) {
        if (snapshot.hasData) {
          final analysis = snapshot.data!;
          return Container(
            padding: EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.green.shade50,
              borderRadius: BorderRadius.circular(12)
            ),
            child: Column(
              children: [
                Text('🧠 Predicción GBGCN', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: [
                    _buildPredictionMetric('📊 Prob. éxito', analysis.successProbability),
                    _buildPredictionMetric('⏱️ Tiempo formación', '${analysis.estimatedHours}h'),
                    _buildPredictionMetric('👥 Tamaño óptimo', analysis.optimalSize.toString())
                  ]
                ),
                
                if (analysis.recommendedParticipants.isNotEmpty)
                  Column(
                    children: [
                      SizedBox(height: 12),
                      Text('💡 Usuarios sugeridos:', style: TextStyle(fontWeight: FontWeight.w600)),
                      Wrap(
                        children: analysis.recommendedParticipants.map((user) => 
                          Chip(label: Text(user.username))
                        ).toList()
                      )
                    ]
                  )
              ]
            )
          );
        }
        return CircularProgressIndicator();
      }
    );
  }
}
```

## 🔗 **ENDPOINTS CLAVE PARA FLUTTER**

### **1. RECOMENDACIONES (Uso frecuente)**
```dart
class GBGCNApiService {
  final String baseUrl = 'http://your-api.com/api/v1';
  
  // 🎯 Obtener recomendaciones principales
  Future<List<ItemRecommendation>> getRecommendations({
    int limit = 10,
    bool includeSocialInfluence = true,
    double minSuccessProbability = 0.1
  }) async {
    final response = await dio.get(
      '$baseUrl/recommendations/items',
      queryParameters: {
        'limit': limit,
        'include_social_influence': includeSocialInfluence,
        'min_success_probability': minSuccessProbability
      },
      options: Options(headers: {'Authorization': 'Bearer $token'})
    );
    
    return (response.data as List)
        .map((item) => ItemRecommendation.fromJson(item))
        .toList();
  }
  
  // 👥 Obtener grupos recomendados para unirse
  Future<List<GroupRecommendation>> getRecommendedGroups({
    int limit = 10,
    double minSuccessProbability = 0.3
  }) async {
    final response = await dio.get(
      '$baseUrl/recommendations/groups',
      queryParameters: {
        'limit': limit,
        'min_success_probability': minSuccessProbability
      },
      options: Options(headers: {'Authorization': 'Bearer $token'})
    );
    
    return (response.data as List)
        .map((group) => GroupRecommendation.fromJson(group))
        .toList();
  }
  
  // 🔍 Analizar potencial de formación de grupo
  Future<GroupFormationAnalysis> analyzeGroupFormation({
    required String itemId,
    required int targetQuantity,
    List<String> potentialParticipants = const []
  }) async {
    final response = await dio.post(
      '$baseUrl/recommendations/groups/analyze',
      data: {
        'item_id': itemId,
        'target_quantity': targetQuantity,
        'potential_participants': potentialParticipants,
        'max_participants': 20
      },
      options: Options(headers: {'Authorization': 'Bearer $token'})
    );
    
    return GroupFormationAnalysis.fromJson(response.data);
  }
  
  // 🤝 Obtener análisis de influencia social
  Future<SocialInfluenceAnalysis> getSocialInfluenceAnalysis({
    required String userId,
    String? itemId
  }) async {
    final response = await dio.get(
      '$baseUrl/recommendations/social-influence/$userId',
      queryParameters: itemId != null ? {'item_id': itemId} : null,
      options: Options(headers: {'Authorization': 'Bearer $token'})
    );
    
    return SocialInfluenceAnalysis.fromJson(response.data);
  }
}
```

### **2. GESTIÓN DE GRUPOS**
```dart
// 🚀 Crear grupo con optimización GBGCN
Future<GroupResponse> createGroup(GroupCreateRequest request) async {
  final response = await dio.post(
    '$baseUrl/groups/',
    data: request.toJson(),
    options: Options(headers: {'Authorization': 'Bearer $token'})
  );
  
  return GroupResponse.fromJson(response.data);
}

// 👥 Unirse a grupo
Future<void> joinGroup(String groupId, {String? message}) async {
  await dio.post(
    '$baseUrl/groups/$groupId/join',
    data: {'message': message},
    options: Options(headers: {'Authorization': 'Bearer $token'})
  );
}

// 📊 Obtener detalles completos del grupo
Future<GroupResponse> getGroupDetails(String groupId) async {
  final response = await dio.get(
    '$baseUrl/groups/$groupId',
    options: Options(headers: {'Authorization': 'Bearer $token'})
  );
  
  return GroupResponse.fromJson(response.data);
}
```

## 🎨 **UI/UX ESPECÍFICO PARA GBGCN**

### **1. COLORES Y VISUALIZACIÓN DE SCORES**
```dart
class GBGCNTheme {
  // Colores para scores
  static Color getScoreColor(double score) {
    if (score >= 0.8) return Colors.green;
    if (score >= 0.6) return Colors.orange;
    if (score >= 0.4) return Colors.blue;
    return Colors.red;
  }
  
  // Iconos para tipos de recomendación
  static IconData getRecommendationIcon(String type) {
    switch (type) {
      case 'initiate': return Icons.rocket_launch;
      case 'join': return Icons.group_add;
      default: return Icons.recommend;
    }
  }
}
```

### **2. WIDGETS PERSONALIZADOS**
```dart
class GBGCNScoreWidget extends StatelessWidget {
  final double score;
  final String label;
  
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: GBGCNTheme.getScoreColor(score).withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: GBGCNTheme.getScoreColor(score))
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.psychology, size: 16, color: GBGCNTheme.getScoreColor(score)),
          SizedBox(width: 4),
          Text(
            '$label: ${(score * 100).toInt()}%',
            style: TextStyle(
              color: GBGCNTheme.getScoreColor(score),
              fontWeight: FontWeight.w600,
              fontSize: 12
            )
          )
        ]
      )
    );
  }
}

class GroupSuccessProbabilityIndicator extends StatelessWidget {
  final double probability;
  
  Widget build(BuildContext context) {
    return LinearProgressIndicator(
      value: probability,
      backgroundColor: Colors.grey.shade300,
      valueColor: AlwaysStoppedAnimation<Color>(
        probability > 0.7 ? Colors.green : 
        probability > 0.4 ? Colors.orange : Colors.red
      ),
    );
  }
}
```

## 🔄 **FLUJOS DE USUARIO CLAVE**

### **1. FLUJO DE DESCUBRIMIENTO**
```
📱 App Launch → 
🔐 Login → 
🧠 GBGCN carga recomendaciones → 
📦 Usuario ve productos sugeridos →
🎯 Tap en recomendación →
📊 Ve predicciones GBGCN →
👥 Decide crear o unirse a grupo
```

### **2. FLUJO DE CREACIÓN DE GRUPO**
```
📦 Producto seleccionado →
🚀 "Crear Grupo" →
🧠 GBGCN analiza potencial →
📊 Muestra predicciones →
⚙️ Usuario configura grupo →
💡 GBGCN sugiere participantes →
✅ Crear grupo optimizado
```

### **3. FLUJO DE UNIÓN A GRUPO**
```
👥 Ver grupos recomendados →
🧠 GBGCN muestra compatibilidad →
📊 Ver probabilidad de éxito →
🤝 Ver conexiones sociales →
✅ Unirse al grupo
```

## 📊 **MODELOS DE DATOS FLUTTER**

```dart
class ItemRecommendation {
  final String itemId;
  final String title;
  final String description;
  final double regularPrice;
  final double predictedDiscount;
  final double successProbability;
  final double socialInfluenceScore;
  final double recommendationScore;
  final String recommendationReason;
  final String recommendationType; // 'initiate' | 'join'
  
  factory ItemRecommendation.fromJson(Map<String, dynamic> json) {
    return ItemRecommendation(
      itemId: json['item_id'],
      title: json['title'],
      description: json['description'],
      regularPrice: json['regular_price'].toDouble(),
      predictedDiscount: json['predicted_discount'].toDouble(),
      successProbability: json['success_probability'].toDouble(),
      socialInfluenceScore: json['social_influence_score'].toDouble(),
      recommendationScore: json['recommendation_score']?.toDouble() ?? 0.0,
      recommendationReason: json['recommendation_reason'] ?? '',
      recommendationType: json['recommendation_type'] ?? 'initiate'
    );
  }
}

class GroupRecommendation {
  final String groupId;
  final String title;
  final String itemId;
  final int currentMembers;
  final int targetSize;
  final double successProbability;
  final double compatibilityScore;
  final int socialConnections;
  final int estimatedCompletionDays;
  
  factory GroupRecommendation.fromJson(Map<String, dynamic> json) {
    return GroupRecommendation(
      groupId: json['group_id'],
      title: json['title'],
      itemId: json['item_id'],
      currentMembers: json['current_members'],
      targetSize: json['target_size'],
      successProbability: json['success_probability'].toDouble(),
      compatibilityScore: json['compatibility_score'].toDouble(),
      socialConnections: json['social_connections'],
      estimatedCompletionDays: json['estimated_completion_days']
    );
  }
}
```

## 🚀 **IMPLEMENTACIÓN PASO A PASO**

### **FASE 1: Setup Básico (Semana 1)**
1. ✅ Configurar HTTP client (dio)
2. ✅ Implementar autenticación JWT
3. ✅ Crear modelos de datos GBGCN
4. ✅ Setup navegación entre pantallas

### **FASE 2: Recomendaciones (Semana 2)**
1. ✅ Pantalla de recomendaciones principales
2. ✅ Integrar endpoint `/recommendations/items`
3. ✅ UI para mostrar scores GBGCN
4. ✅ Filtros inteligentes

### **FASE 3: Grupos (Semana 3)**
1. ✅ Pantalla de creación de grupos
2. ✅ Análisis de formación de grupos
3. ✅ Pantalla de detalles de grupo
4. ✅ Funcionalidad unirse/salir

### **FASE 4: Optimización (Semana 4)**
1. ✅ Cache de recomendaciones
2. ✅ Push notifications
3. ✅ Analytics y métricas
4. ✅ Testing y optimización

## 💡 **BEST PRACTICES**

### **1. PERFORMANCE**
- Cache recomendaciones por 15 minutos
- Lazy loading para listas largas
- Preload datos de grupos sugeridos

### **2. UX**
- Mostrar scores de manera visual (colores, gráficos)
- Explicar por qué se recomienda algo
- Feedback inmediato en acciones

### **3. DATOS**
- Sincronizar preferencias del usuario
- Tracking de interacciones para mejorar GBGCN
- Offline support para funciones básicas

## 🎯 **MÉTRICAS A TRACKEAR**

```dart
class GBGCNAnalytics {
  // Trackear interacciones con recomendaciones
  void trackRecommendationClick(String itemId, double score) {
    analytics.logEvent('gbgcn_recommendation_click', {
      'item_id': itemId,
      'recommendation_score': score,
      'timestamp': DateTime.now().toIso8601String()
    });
  }
  
  // Trackear creación de grupos
  void trackGroupCreation(String groupId, double predictedSuccess) {
    analytics.logEvent('gbgcn_group_created', {
      'group_id': groupId,
      'predicted_success': predictedSuccess,
      'timestamp': DateTime.now().toIso8601String()
    });
  }
  
  // Trackear unión a grupos
  void trackGroupJoin(String groupId, double compatibilityScore) {
    analytics.logEvent('gbgcn_group_joined', {
      'group_id': groupId,
      'compatibility_score': compatibilityScore,
      'timestamp': DateTime.now().toIso8601String()
    });
  }
}
```

---

## ✅ **RESUMEN EJECUTIVO**

**Tu app de Flutter debe:**

1. **🎯 Mostrar recomendaciones GBGCN prominentemente** en home
2. **📊 Visualizar scores y probabilidades** de manera clara
3. **🚀 Facilitar creación de grupos** con predicciones inteligentes
4. **👥 Sugerir grupos para unirse** basado en compatibilidad
5. **📈 Trackear métricas** para mejorar el modelo
6. **🔄 Actualizar datos** frecuentemente para mantener relevancia

**El resultado:** Una experiencia de e-commerce revolucionaria donde el AI GBGCN guía a los usuarios hacia compras grupales exitosas con alta probabilidad de ahorro y satisfacción. 