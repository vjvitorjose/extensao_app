import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class UserProfileProvider extends ChangeNotifier {
  final supabase = Supabase.instance.client;

  // Dados do Perfil
  String _nomeCompleto = 'Carregando...';
  String _email = '';
  String _telefone = '';
  String _cpf = '';

  // Lista dinâmica para múltiplos contatos de emergência
  List<Map<String, dynamic>> _contatosEmergencia = [];

  bool _isLoading = true;

  // Getters
  String get nomeCompleto => _nomeCompleto;
  String get email => _email;
  String get telefone => _telefone;
  String get cpf => _cpf;
  List<Map<String, dynamic>> get contatosEmergencia => _contatosEmergencia;
  bool get isLoading => _isLoading;

  /// Carrega o perfil e a lista de contatos do Supabase
  Future<void> loadProfile() async {
    _isLoading = true;
    notifyListeners();

    try {
      final user = supabase.auth.currentUser;
      if (user == null) {
        _isLoading = false;
        notifyListeners();
        return;
      }

      _email = user.email ?? 'Sem e-mail';

      // 1. Busca os dados do perfil básico
      final perfilDados = await supabase
          .from('profiles')
          .select()
          .eq('id', user.id)
          .maybeSingle();

      if (perfilDados != null) {
        _nomeCompleto = perfilDados['nome_completo'] ?? 'Usuária vigIA';
        _telefone = perfilDados['telefone'] ?? '';
        _cpf = perfilDados['cpf'] ?? '';
      } else {
        _nomeCompleto = 'Usuária vigIA';
      }

      // 2. Busca a lista de múltiplos contatos de emergência
      final contatosDados = await supabase
          .from('emergency_contacts')
          .select()
          .eq('profile_id', user.id)
          .order('criado_em', ascending: true);

      _contatosEmergencia = List<Map<String, dynamic>>.from(contatosDados);
    } catch (e) {
      debugPrint('Erro ao carregar dados do perfil: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Atualiza os dados básicos do perfil
  Future<void> updateProfile({
    required String nomeCompleto,
    required String telefone,
    required String cpf,
  }) async {
    final user = supabase.auth.currentUser;
    if (user == null) return;

    try {
      await supabase.from('profiles').upsert({
        'id': user.id,
        'nome_completo': nomeCompleto,
        'telefone': telefone,
        'cpf': cpf.trim(),
        'atualizado_em': DateTime.now().toIso8601String(),
      });

      _nomeCompleto = nomeCompleto;
      _telefone = telefone;
      _cpf = cpf;
      notifyListeners();
    } catch (e) {
      debugPrint('Erro ao salvar perfil: $e');
      rethrow;
    }
  }

  /// Adiciona um novo contato de emergência
  Future<void> addEmergencyContact({
    required String nome,
    required String telefone,
    String? email,
    String? parentesco,
  }) async {
    final user = supabase.auth.currentUser;
    if (user == null) return;

    try {
      await supabase.from('emergency_contacts').insert({
        'profile_id': user.id,
        'nome': nome,
        'telefone': telefone,
        'email': email?.trim(),
        'parentesco': parentesco,
      });

      // Recarrega a lista de contatos
      await loadProfile();
    } catch (e) {
      debugPrint('Erro ao adicionar contato: $e');
      rethrow;
    }
  }

  /// Remove um contato específico da tabela
  Future<void> removeEmergencyContact(String contatoId) async {
    try {
      await supabase.from('emergency_contacts').delete().eq('id', contatoId);

      // Remove da lista local
      _contatosEmergencia.removeWhere((c) => c['id'].toString() == contatoId);
      notifyListeners();
    } catch (e) {
      debugPrint('Erro ao deletar contato: $e');
      rethrow;
    }
  }
}
