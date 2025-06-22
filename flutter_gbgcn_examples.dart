// 📱 FLUTTER + GBGCN - EJEMPLOS DE CÓDIGO ESPECÍFICOS
// Implementaciones reales para tu app de e-commerce

import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import 'package:provider/provider.dart';

// ==========================================
// 🧠 GBGCN SERVICE - CLIENTE API
// ==========================================

class GBGCNService {
  final Dio _dio;
  final String baseUrl = 'http://localhost:8000/api/v1';
  
  GBGCNService(this._dio);
  
  /// 🎯 OBTENER RECOMENDACIONES PRINCIPALES
  Future<List<ItemRecommendation>> getPersonalizedRecommendations({
    int limit = 10,
    bool includeSocialInfluence = true,
    double minSuccessProbability = 0.1,
  }) async {
    try {
      final response = await _dio.get(
        '$baseUrl/recommendations/',
        queryParameters: {
          'limit': limit,
          'include_social_influence': includeSocialInfluence,
          'min_success_probability': minSuccessProbability,
        },
      );
      
      return (response.data as List)
          .map((json) => ItemRecommendation.fromJson(json))
          .toList();
    } catch (e) {
      print('❌ Error getting recommendations: $e');
      return [];
    }
  }
  
  /// 👥 OBTENER GRUPOS RECOMENDADOS
  Future<List<GroupRecommendation>> getRecommendedGroups({
    int limit = 10,
    double minSuccessProbability = 0.3,
  }) async {
    try {
      final response = await _dio.get(
        '$baseUrl/groups/',
        queryParameters: {
          'limit': limit,
          'status_filter': 'FORMING',
          'sort_by': 'success_probability',
          'sort_order': 'desc',
        },
      );
      
      return (response.data as List)
          .map((json) => GroupRecommendation.fromJson(json))
          .where((group) => group.successProbability >= minSuccessProbability)
          .toList();
    } catch (e) {
      print('❌ Error getting group recommendations: $e');
      return [];
    }
  }
  
  /// 🔍 ANALIZAR POTENCIAL DE GRUPO
  Future<GroupFormationAnalysis?> analyzeGroupFormation({
    required String itemId,
    required int targetQuantity,
    List<String> potentialParticipants = const [],
  }) async {
    try {
      final response = await _dio.post(
        '$baseUrl/recommendations/groups/analyze',
        data: {
          'item_id': itemId,
          'target_quantity': targetQuantity,
          'potential_participants': potentialParticipants,
          'max_participants': 20,
        },
      );
      
      return GroupFormationAnalysis.fromJson(response.data);
    } catch (e) {
      print('❌ Error analyzing group formation: $e');
      return null;
    }
  }
  
  /// 🚀 CREAR GRUPO OPTIMIZADO
  Future<GroupResponse?> createOptimizedGroup({
    required String itemId,
    required String title,
    required String description,
    required int targetSize,
    required double targetPrice,
    int durationDays = 7,
  }) async {
    try {
      final response = await _dio.post(
        '$baseUrl/groups/',
        data: {
          'item_id': itemId,
          'title': title,
          'description': description,
          'target_size': targetSize,
          'min_size': (targetSize * 0.6).round(), // 60% del target como mínimo
          'target_price': targetPrice,
          'duration_days': durationDays,
          'is_public': true,
        },
      );
      
      return GroupResponse.fromJson(response.data);
    } catch (e) {
      print('❌ Error creating group: $e');
      return null;
    }
  }
}

// ==========================================
// 📊 MODELOS DE DATOS GBGCN
// ==========================================

class ItemRecommendation {
  final String itemId;
  final String itemName;
  final String description;
  final double recommendationScore;
  final double successProbability;
  final double socialInfluenceScore;
  final String recommendationType; // 'initiate' | 'join'
  final double predictedPrice;
  final int targetGroupSize;
  final String modelVersion;
  
  ItemRecommendation({
    required this.itemId,
    required this.itemName,
    required this.description,
    required this.recommendationScore,
    required this.successProbability,
    required this.socialInfluenceScore,
    required this.recommendationType,
    required this.predictedPrice,
    required this.targetGroupSize,
    required this.modelVersion,
  });
  
  factory ItemRecommendation.fromJson(Map<String, dynamic> json) {
    return ItemRecommendation(
      itemId: json['item_id'] ?? '',
      itemName: json['item_name'] ?? '',
      description: json['description'] ?? '',
      recommendationScore: (json['recommendation_score'] ?? 0.0).toDouble(),
      successProbability: (json['success_probability'] ?? 0.0).toDouble(),
      socialInfluenceScore: (json['social_influence_score'] ?? 0.0).toDouble(),
      recommendationType: json['recommendation_type'] ?? 'initiate',
      predictedPrice: (json['predicted_price'] ?? 0.0).toDouble(),
      targetGroupSize: json['target_group_size'] ?? 0,
      modelVersion: json['model_version'] ?? 'gbgcn_v1.0',
    );
  }
  
  // Helper methods
  Color get scoreColor {
    if (recommendationScore >= 0.8) return Colors.green;
    if (recommendationScore >= 0.6) return Colors.orange;
    if (recommendationScore >= 0.4) return Colors.blue;
    return Colors.red;
  }
  
  IconData get typeIcon {
    return recommendationType == 'initiate' 
        ? Icons.rocket_launch 
        : Icons.group_add;
  }
  
  String get confidenceLevel {
    if (recommendationScore >= 0.9) return 'Muy Alta';
    if (recommendationScore >= 0.7) return 'Alta';
    if (recommendationScore >= 0.5) return 'Media';
    return 'Baja';
  }
}

class GroupRecommendation {
  final String groupId;
  final String title;
  final String itemId;
  final int currentQuantity;
  final int targetQuantity;
  final double totalAmount;
  final String status;
  final double successProbability;
  final double socialInfluenceScore;
  final DateTime createdAt;
  
  GroupRecommendation({
    required this.groupId,
    required this.title,
    required this.itemId,
    required this.currentQuantity,
    required this.targetQuantity,
    required this.totalAmount,
    required this.status,
    required this.successProbability,
    required this.socialInfluenceScore,
    required this.createdAt,
  });
  
  factory GroupRecommendation.fromJson(Map<String, dynamic> json) {
    return GroupRecommendation(
      groupId: json['id'] ?? '',
      title: json['title'] ?? '',
      itemId: json['item_id'] ?? '',
      currentQuantity: json['current_quantity'] ?? 0,
      targetQuantity: json['target_quantity'] ?? 0,
      totalAmount: (json['total_amount'] ?? 0.0).toDouble(),
      status: json['status'] ?? '',
      successProbability: (json['success_probability'] ?? 0.0).toDouble(),
      socialInfluenceScore: (json['social_influence_score'] ?? 0.0).toDouble(),
      createdAt: DateTime.parse(json['created_at'] ?? DateTime.now().toIso8601String()),
    );
  }
  
  double get completionPercentage => currentQuantity / targetQuantity;
  
  Color get statusColor {
    switch (status.toUpperCase()) {
      case 'FORMING':
        return Colors.blue;
      case 'ACTIVE':
        return Colors.green;
      case 'COMPLETED':
        return Colors.purple;
      default:
        return Colors.grey;
    }
  }
}

// ==========================================
// 🏠 PANTALLA PRINCIPAL CON GBGCN
// ==========================================

class GBGCNHomeScreen extends StatefulWidget {
  @override
  _GBGCNHomeScreenState createState() => _GBGCNHomeScreenState();
}

class _GBGCNHomeScreenState extends State<GBGCNHomeScreen> {
  final GBGCNService _gbgcnService = GBGCNService(Dio());
  List<ItemRecommendation> _recommendations = [];
  List<GroupRecommendation> _suggestedGroups = [];
  bool _isLoading = true;
  
  @override
  void initState() {
    super.initState();
    _loadGBGCNData();
  }
  
  Future<void> _loadGBGCNData() async {
    setState(() => _isLoading = true);
    
    try {
      final recommendations = await _gbgcnService.getPersonalizedRecommendations(limit: 5);
      final groups = await _gbgcnService.getRecommendedGroups(limit: 5);
      
      setState(() {
        _recommendations = recommendations;
        _suggestedGroups = groups;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('❌ Error cargando recomendaciones: $e'))
      );
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('🧠 GBGCN E-Commerce'),
        backgroundColor: Colors.blue.shade700,
        foregroundColor: Colors.white,
      ),
      body: _isLoading
          ? Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadGBGCNData,
              child: SingleChildScrollView(
                padding: EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildWelcomeSection(),
                    SizedBox(height: 24),
                    _buildRecommendationsSection(),
                    SizedBox(height: 24),
                    _buildSuggestedGroupsSection(),
                  ],
                ),
              ),
            ),
    );
  }
  
  Widget _buildWelcomeSection() {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [Colors.blue.shade600, Colors.purple.shade600],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '🎯 Recomendaciones Personalizadas',
            style: TextStyle(
              color: Colors.white,
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          SizedBox(height: 8),
          Text(
            'Basadas en tu comportamiento y conexiones sociales',
            style: TextStyle(color: Colors.white.withOpacity(0.9), fontSize: 14),
          ),
          SizedBox(height: 12),
          Row(
            children: [
              Icon(Icons.psychology, color: Colors.white, size: 16),
              SizedBox(width: 4),
              Text(
                'Potenciado por GBGCN AI',
                style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w500),
              ),
            ],
          ),
        ],
      ),
    );
  }
  
  Widget _buildRecommendationsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              '🔥 Para ti',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            TextButton(
              onPressed: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => GBGCNRecommendationsScreen()),
              ),
              child: Text('Ver todas'),
            ),
          ],
        ),
        SizedBox(height: 12),
        Container(
          height: 280,
          child: ListView.builder(
            scrollDirection: Axis.horizontal,
            itemCount: _recommendations.length,
            itemBuilder: (context, index) {
              return _buildRecommendationCard(_recommendations[index]);
            },
          ),
        ),
      ],
    );
  }
  
  Widget _buildRecommendationCard(ItemRecommendation recommendation) {
    return Container(
      width: 200,
      margin: EdgeInsets.only(right: 12),
      child: Card(
        elevation: 4,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: Padding(
          padding: EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Score badge
              Container(
                padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: recommendation.scoreColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: recommendation.scoreColor),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.psychology, size: 12, color: recommendation.scoreColor),
                    SizedBox(width: 4),
                    Text(
                      '${(recommendation.recommendationScore * 100).toInt()}%',
                      style: TextStyle(
                        color: recommendation.scoreColor,
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
              
              SizedBox(height: 8),
              
              // Product name
              Text(
                recommendation.itemName,
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              
              SizedBox(height: 8),
              
              // GBGCN metrics
              _buildMetricRow('📊 Éxito', '${(recommendation.successProbability * 100).toInt()}%'),
              _buildMetricRow('🤝 Social', '${(recommendation.socialInfluenceScore * 100).toInt()}%'),
              _buildMetricRow('👥 Grupo', '${recommendation.targetGroupSize} personas'),
              _buildMetricRow('💰 Precio', '\$${recommendation.predictedPrice.toStringAsFixed(2)}'),
              
              Spacer(),
              
              // Action button
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: () => _handleRecommendationAction(recommendation),
                  icon: Icon(recommendation.typeIcon, size: 16),
                  label: Text(
                    recommendation.recommendationType == 'initiate' ? 'Crear Grupo' : 'Unirse',
                    style: TextStyle(fontSize: 12),
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: recommendation.scoreColor,
                    foregroundColor: Colors.white,
                    padding: EdgeInsets.symmetric(vertical: 8),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildMetricRow(String label, String value) {
    return Padding(
      padding: EdgeInsets.symmetric(vertical: 2),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TextStyle(fontSize: 10, color: Colors.grey.shade600)),
          Text(value, style: TextStyle(fontSize: 10, fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }
  
  Widget _buildSuggestedGroupsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '👥 Grupos Sugeridos',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
        ),
        SizedBox(height: 12),
        Column(
          children: _suggestedGroups.map((group) => _buildGroupCard(group)).toList(),
        ),
      ],
    );
  }
  
  Widget _buildGroupCard(GroupRecommendation group) {
    return Card(
      margin: EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: group.statusColor,
          child: Text(
            '${(group.successProbability * 100).toInt()}%',
            style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
          ),
        ),
        title: Text(group.title, style: TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('👥 ${group.currentQuantity}/${group.targetQuantity} participantes'),
            LinearProgressIndicator(
              value: group.completionPercentage,
              backgroundColor: Colors.grey.shade300,
              valueColor: AlwaysStoppedAnimation<Color>(group.statusColor),
            ),
          ],
        ),
        trailing: ElevatedButton(
          onPressed: () => _joinGroup(group.groupId),
          child: Text('Unirse'),
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.green,
            foregroundColor: Colors.white,
          ),
        ),
      ),
    );
  }
  
  void _handleRecommendationAction(ItemRecommendation recommendation) {
    if (recommendation.recommendationType == 'initiate') {
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => CreateGroupScreen(
            itemId: recommendation.itemId,
            itemName: recommendation.itemName,
            suggestedPrice: recommendation.predictedPrice,
            suggestedSize: recommendation.targetGroupSize,
          ),
        ),
      );
    } else {
      // Navigate to join existing group
      _findAndJoinGroup(recommendation.itemId);
    }
  }
  
  void _joinGroup(String groupId) async {
    try {
      // Implement join group logic
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('✅ Te has unido al grupo exitosamente')),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('❌ Error uniéndose al grupo: $e')),
      );
    }
  }
  
  void _findAndJoinGroup(String itemId) {
    // Navigate to groups list filtered by item
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => GroupsListScreen(itemFilter: itemId),
      ),
    );
  }
}

// ==========================================
// 🚀 PANTALLA DE CREACIÓN DE GRUPO
// ==========================================

class CreateGroupScreen extends StatefulWidget {
  final String itemId;
  final String itemName;
  final double suggestedPrice;
  final int suggestedSize;
  
  CreateGroupScreen({
    required this.itemId,
    required this.itemName,
    required this.suggestedPrice,
    required this.suggestedSize,
  });
  
  @override
  _CreateGroupScreenState createState() => _CreateGroupScreenState();
}

class _CreateGroupScreenState extends State<CreateGroupScreen> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _targetSizeController = TextEditingController();
  final _targetPriceController = TextEditingController();
  
  final GBGCNService _gbgcnService = GBGCNService(Dio());
  GroupFormationAnalysis? _analysis;
  bool _isAnalyzing = false;
  
  @override
  void initState() {
    super.initState();
    _targetSizeController.text = widget.suggestedSize.toString();
    _targetPriceController.text = widget.suggestedPrice.toStringAsFixed(2);
    _titleController.text = 'Grupo para ${widget.itemName}';
    _analyzeGroupFormation();
  }
  
  Future<void> _analyzeGroupFormation() async {
    setState(() => _isAnalyzing = true);
    
    final analysis = await _gbgcnService.analyzeGroupFormation(
      itemId: widget.itemId,
      targetQuantity: widget.suggestedSize,
    );
    
    setState(() {
      _analysis = analysis;
      _isAnalyzing = false;
    });
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('🚀 Crear Grupo'),
        backgroundColor: Colors.green.shade700,
        foregroundColor: Colors.white,
      ),
      body: Form(
        key: _formKey,
        child: SingleChildScrollView(
          padding: EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildProductInfo(),
              SizedBox(height: 20),
              _buildGBGCNAnalysis(),
              SizedBox(height: 20),
              _buildGroupForm(),
              SizedBox(height: 20),
              _buildCreateButton(),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildProductInfo() {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.blue.shade50,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.blue.shade200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('📦 Producto', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          SizedBox(height: 8),
          Text(widget.itemName, style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
          SizedBox(height: 4),
          Text('ID: ${widget.itemId}', style: TextStyle(color: Colors.grey.shade600)),
        ],
      ),
    );
  }
  
  Widget _buildGBGCNAnalysis() {
    if (_isAnalyzing) {
      return Container(
        padding: EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: Colors.orange.shade50,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            CircularProgressIndicator(strokeWidth: 2),
            SizedBox(width: 16),
            Text('🧠 Analizando con GBGCN...'),
          ],
        ),
      );
    }
    
    if (_analysis == null) {
      return Container(
        padding: EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.red.shade50,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Text('❌ No se pudo analizar el grupo. Continúa sin predicciones.'),
      );
    }
    
    return Container(
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.green.shade50,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.green.shade200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.psychology, color: Colors.green.shade700),
              SizedBox(width: 8),
              Text(
                '🧠 Predicciones GBGCN',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.green.shade700),
              ),
            ],
          ),
          SizedBox(height: 16),
          
          Row(
            children: [
              Expanded(child: _buildPredictionMetric('📊 Prob. Éxito', '${(_analysis!.successProbability * 100).toInt()}%', Colors.green)),
              Expanded(child: _buildPredictionMetric('⏱️ Tiempo Est.', '${_analysis!.estimatedFormationTimeHours}h', Colors.blue)),
              Expanded(child: _buildPredictionMetric('👥 Tamaño Óptimo', _analysis!.optimalSize.toString(), Colors.purple)),
            ],
          ),
          
          if (_analysis!.recommendedParticipants.isNotEmpty) ...[
            SizedBox(height: 16),
            Text('💡 Participantes sugeridos:', style: TextStyle(fontWeight: FontWeight.w600)),
            SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: _analysis!.recommendedParticipants.map((participant) => 
                Chip(
                  label: Text(participant, style: TextStyle(fontSize: 12)),
                  backgroundColor: Colors.blue.shade100,
                )
              ).toList(),
            ),
          ],
          
          if (_analysis!.riskFactors.isNotEmpty) ...[
            SizedBox(height: 12),
            Text('⚠️ Factores de riesgo:', style: TextStyle(fontWeight: FontWeight.w600, color: Colors.orange.shade700)),
            ...(_analysis!.riskFactors.map((risk) => 
              Padding(
                padding: EdgeInsets.only(left: 16, top: 4),
                child: Text('• $risk', style: TextStyle(color: Colors.orange.shade700)),
              )
            )),
          ],
        ],
      ),
    );
  }
  
  Widget _buildPredictionMetric(String label, String value, Color color) {
    return Container(
      padding: EdgeInsets.all(12),
      margin: EdgeInsets.symmetric(horizontal: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color),
      ),
      child: Column(
        children: [
          Text(value, style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: color)),
          SizedBox(height: 4),
          Text(label, style: TextStyle(fontSize: 10, color: color), textAlign: TextAlign.center),
        ],
      ),
    );
  }
  
  Widget _buildGroupForm() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('⚙️ Configuración del Grupo', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        SizedBox(height: 16),
        
        TextFormField(
          controller: _titleController,
          decoration: InputDecoration(
            labelText: 'Título del grupo',
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
          ),
          validator: (value) => value?.isEmpty == true ? 'Ingresa un título' : null,
        ),
        
        SizedBox(height: 16),
        
        TextFormField(
          controller: _descriptionController,
          decoration: InputDecoration(
            labelText: 'Descripción',
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
          ),
          maxLines: 3,
          validator: (value) => value?.isEmpty == true ? 'Ingresa una descripción' : null,
        ),
        
        SizedBox(height: 16),
        
        Row(
          children: [
            Expanded(
              child: TextFormField(
                controller: _targetSizeController,
                decoration: InputDecoration(
                  labelText: 'Tamaño objetivo',
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                  suffixText: 'personas',
                ),
                keyboardType: TextInputType.number,
                validator: (value) {
                  final size = int.tryParse(value ?? '');
                  if (size == null || size < 2) return 'Mínimo 2 personas';
                  if (size > 50) return 'Máximo 50 personas';
                  return null;
                },
              ),
            ),
            SizedBox(width: 16),
            Expanded(
              child: TextFormField(
                controller: _targetPriceController,
                decoration: InputDecoration(
                  labelText: 'Precio objetivo',
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                  prefixText: '\$',
                ),
                keyboardType: TextInputType.numberWithOptions(decimal: true),
                validator: (value) {
                  final price = double.tryParse(value ?? '');
                  if (price == null || price <= 0) return 'Precio inválido';
                  return null;
                },
              ),
            ),
          ],
        ),
      ],
    );
  }
  
  Widget _buildCreateButton() {
    return SizedBox(
      width: double.infinity,
      height: 50,
      child: ElevatedButton.icon(
        onPressed: _createGroup,
        icon: Icon(Icons.rocket_launch),
        label: Text('🚀 Crear Grupo Inteligente', style: TextStyle(fontSize: 16)),
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.green.shade600,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
      ),
    );
  }
  
  void _createGroup() async {
    if (!_formKey.currentState!.validate()) return;
    
    try {
      final group = await _gbgcnService.createOptimizedGroup(
        itemId: widget.itemId,
        title: _titleController.text,
        description: _descriptionController.text,
        targetSize: int.parse(_targetSizeController.text),
        targetPrice: double.parse(_targetPriceController.text),
      );
      
      if (group != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('✅ Grupo creado exitosamente')),
        );
        Navigator.pop(context);
      } else {
        throw Exception('Error creando grupo');
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('❌ Error: $e')),
      );
    }
  }
}

// ==========================================
// 📊 MODELOS AUXILIARES
// ==========================================

class GroupFormationAnalysis {
  final String itemId;
  final double successProbability;
  final int optimalSize;
  final List<String> recommendedParticipants;
  final int estimatedFormationTimeHours;
  final List<String> riskFactors;
  
  GroupFormationAnalysis({
    required this.itemId,
    required this.successProbability,
    required this.optimalSize,
    required this.recommendedParticipants,
    required this.estimatedFormationTimeHours,
    required this.riskFactors,
  });
  
  factory GroupFormationAnalysis.fromJson(Map<String, dynamic> json) {
    return GroupFormationAnalysis(
      itemId: json['item_id'] ?? '',
      successProbability: (json['success_probability'] ?? 0.0).toDouble(),
      optimalSize: json['optimal_size'] ?? 0,
      recommendedParticipants: List<String>.from(json['recommended_participants'] ?? []),
      estimatedFormationTimeHours: json['estimated_formation_time_hours'] ?? 0,
      riskFactors: List<String>.from(json['risk_factors'] ?? []),
    );
  }
}

class GroupResponse {
  final String id;
  final String title;
  final String description;
  final String itemId;
  final int targetSize;
  final double targetPrice;
  final String status;
  final double successProbability;
  final DateTime createdAt;
  
  GroupResponse({
    required this.id,
    required this.title,
    required this.description,
    required this.itemId,
    required this.targetSize,
    required this.targetPrice,
    required this.status,
    required this.successProbability,
    required this.createdAt,
  });
  
  factory GroupResponse.fromJson(Map<String, dynamic> json) {
    return GroupResponse(
      id: json['id'] ?? '',
      title: json['title'] ?? '',
      description: json['description'] ?? '',
      itemId: json['item_id'] ?? '',
      targetSize: json['target_size'] ?? 0,
      targetPrice: (json['target_price'] ?? 0.0).toDouble(),
      status: json['status'] ?? '',
      successProbability: (json['success_probability'] ?? 0.0).toDouble(),
      createdAt: DateTime.parse(json['created_at'] ?? DateTime.now().toIso8601String()),
    );
  }
}

// Placeholders para pantallas adicionales mencionadas
class GBGCNRecommendationsScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('🎯 Todas las Recomendaciones')),
      body: Center(child: Text('Lista completa de recomendaciones GBGCN')),
    );
  }
}

class GroupsListScreen extends StatelessWidget {
  final String? itemFilter;
  
  GroupsListScreen({this.itemFilter});
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('👥 Grupos Disponibles')),
      body: Center(child: Text('Lista de grupos${itemFilter != null ? ' para item $itemFilter' : ''}')),
    );
  }
} 