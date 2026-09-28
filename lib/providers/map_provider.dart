import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:geolocator/geolocator.dart';

class MapProvider extends ChangeNotifier {
  final supabase = Supabase.instance.client;

  LatLng _currentLocation = const LatLng(-21.1355, -44.2616);
  LatLng? _selectedLocation;
  bool _useSelectedLocationForAlert = false;
  bool _isLoadingLocation = true;
  List<Map<String, dynamic>> _dangerReports = [];

  // Getters
  LatLng get currentLocation => _currentLocation;
  LatLng? get selectedLocation => _selectedLocation;
  bool get useSelectedLocationForAlert => _useSelectedLocationForAlert;
  bool get isLoadingLocation => _isLoadingLocation;
  List<Map<String, dynamic>> get dangerReports => _dangerReports;

  /// Obtém a localização atual do usuário
  Future<void> getCurrentLocation() async {
    bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) return;

    LocationPermission permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) return;
    }

    if (permission == LocationPermission.deniedForever) return;

    Position position = await Geolocator.getCurrentPosition();
    _currentLocation = LatLng(position.latitude, position.longitude);
    _isLoadingLocation = false;
    notifyListeners();
  }

  /// Seleciona um local no mapa
  void selectLocation(LatLng location) {
    _selectedLocation = location;
    notifyListeners();
  }

  /// Remove a localização selecionada
  void clearSelectedLocation() {
    _selectedLocation = null;
    notifyListeners();
  }

  /// Define se deve usar o local marcado para alerta
  void setUseSelectedLocationForAlert(bool value) {
    _useSelectedLocationForAlert = value;
    notifyListeners();
  }

  /// Salva um alerta no Supabase
  Future<void> saveAlerta({
    required String categoriaVisual,
    required String descricao,
    required bool isAnonimo,
    required bool usarLocalMarcado,
  }) async {
    final user = supabase.auth.currentUser;

    String tipoBanco = 'area_deserta';
    if (categoriaVisual == 'Assédio') tipoBanco = 'assedio';
    if (categoriaVisual == 'Iluminação ruim') tipoBanco = 'iluminacao_ruim';
    if (categoriaVisual == 'Perseguição') tipoBanco = 'perseguicao';
    if (categoriaVisual == 'Local suspeito') tipoBanco = 'area_deserta';
    if (categoriaVisual == 'Acidente de trânsito') tipoBanco = 'acidente_transito';
    if (categoriaVisual == 'Assalto') tipoBanco = 'assalto';
    if (categoriaVisual == 'Furto') tipoBanco = 'furto';
    if (categoriaVisual == 'Violência física') tipoBanco = 'violencia_fisica';
    if (categoriaVisual == 'Presença de arma') tipoBanco = 'presenca_arma';
    if (categoriaVisual == 'Incêndio ou fumaça') tipoBanco = 'incendio';
    if (categoriaVisual == 'Via bloqueada') tipoBanco = 'via_bloqueada';
    if (categoriaVisual == 'Emergência médica') tipoBanco = 'emergencia_medica';

    try {
      final double lat;
      final double lng;

      if (usarLocalMarcado && _selectedLocation != null) {
        lat = _selectedLocation!.latitude;
        lng = _selectedLocation!.longitude;
      } else {
        final Position posicao = await Geolocator.getCurrentPosition();
        lat = posicao.latitude;
        lng = posicao.longitude;
      }

      await supabase.from('danger_reports').insert({
        'tipo_perigo': tipoBanco,
        'descricao': descricao,
        'latitude': lat,
        'longitude': lng,
        'anonimo': isAnonimo,
        'user_id': user?.id,
        'criado_em': DateTime.now().toIso8601String(),
      });

      // Recarrega os relatórios após salvar
      await loadDangerReports();
    } catch (e) {
      debugPrint('Erro ao salvar alerta: $e');
      rethrow;
    }
  }

  /// Carrega os relatórios de perigo do Supabase
  Future<void> loadDangerReports() async {
    try {
      final response = await supabase.from('danger_reports').select();
      _dangerReports = List<Map<String, dynamic>>.from(response);
      notifyListeners();
    } catch (e) {
      debugPrint('Erro ao carregar relatórios: $e');
    }
  }
}
