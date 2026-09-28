import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AppSettingsProvider extends ChangeNotifier {
  bool _locationSharingEnabled = true;
  bool _pushAlertsEnabled = true;

  // Getters
  bool get locationSharingEnabled => _locationSharingEnabled;
  bool get pushAlertsEnabled => _pushAlertsEnabled;

  /// Carrega as configurações salvas no SharedPreferences
  Future<void> loadSettings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      _locationSharingEnabled = prefs.getBool('location_sharing') ?? true;
      _pushAlertsEnabled = prefs.getBool('push_alerts') ?? true;
      notifyListeners();
    } catch (e) {
      debugPrint('Erro ao carregar configurações: $e');
    }
  }

  /// Alterna o compartilhamento de localização
  Future<void> toggleLocationSharing() async {
    _locationSharingEnabled = !_locationSharingEnabled;
    notifyListeners();

    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool('location_sharing', _locationSharingEnabled);
    } catch (e) {
      debugPrint('Erro ao salvar configuração de localização: $e');
    }
  }

  /// Alterna os alertas por push
  Future<void> togglePushAlerts() async {
    _pushAlertsEnabled = !_pushAlertsEnabled;
    notifyListeners();

    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool('push_alerts', _pushAlertsEnabled);
    } catch (e) {
      debugPrint('Erro ao salvar configuração de alertas: $e');
    }
  }
}
