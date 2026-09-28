import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class AuthProvider extends ChangeNotifier {
  final supabase = Supabase.instance.client;

  User? _currentUser;
  bool _isLoading = true;
  bool _isAdmin = false;
  bool _hasProfileCompleted = false;

  // Getters
  User? get currentUser => _currentUser;
  bool get isLoading => _isLoading;
  bool get isAdmin => _isAdmin;
  bool get hasProfileCompleted => _hasProfileCompleted;
  bool get isLoggedIn => _currentUser != null;

  /// Inicializa o provider e escuta mudanças de autenticação
  void initialize() {
    _escutarAutenticacao();
  }

  /// Escuta mudanças de login/logout/registro em tempo real
  void _escutarAutenticacao() {
    supabase.auth.onAuthStateChange.listen((data) async {
      final session = data.session;

      if (session != null) {
        _currentUser = session.user;
        await _verificarAdmin(session.user.id);
      } else {
        _currentUser = null;
        _isAdmin = false;
        _hasProfileCompleted = false;
        _isLoading = false;
        notifyListeners();
      }
    });
  }

  /// Verifica se o usuário é administrador
  Future<void> _verificarAdmin(String userId) async {
    _isLoading = true;
    notifyListeners();

    try {
      final resposta = await supabase
          .from('administradores')
          .select('id')
          .eq('id', userId)
          .maybeSingle();

      _isAdmin = resposta != null;

      if (_isAdmin) {
        _isLoading = false;
        notifyListeners();
      } else {
        await _verificarPerfilExistente(userId);
      }
    } catch (e) {
      debugPrint('Erro no Gate ao verificar admin: $e');
      _isAdmin = false;
      await _verificarPerfilExistente(userId);
    }
  }

  /// Verifica se o usuário completou o perfil
  Future<void> _verificarPerfilExistente(String userId) async {
    _isLoading = true;
    notifyListeners();

    try {
      final data = await supabase
          .from('profiles')
          .select('nome_completo')
          .eq('id', userId)
          .maybeSingle();

      if (data != null &&
          data['nome_completo'] != null &&
          data['nome_completo'].toString().trim().isNotEmpty) {
        _hasProfileCompleted = true;
      } else {
        _hasProfileCompleted = false;
      }
    } catch (e) {
      debugPrint('Erro no Gate ao verificar perfil: $e');
      _hasProfileCompleted = false;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Faz logout do usuário
  Future<void> signOut() async {
    await supabase.auth.signOut();
    _currentUser = null;
    _isAdmin = false;
    _hasProfileCompleted = false;
    notifyListeners();
  }

  /// Atualiza o status do perfil (após completar onboarding)
  Future<void> refreshProfileStatus() async {
    if (_currentUser != null) {
      await _verificarPerfilExistente(_currentUser!.id);
    }
  }
}
