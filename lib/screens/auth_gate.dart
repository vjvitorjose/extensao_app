import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'login_screen.dart';
import 'main_screen.dart';
import 'onboarding_screen.dart';

class AuthGate extends StatefulWidget {
  const AuthGate({super.key});

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  final supabase = Supabase.instance.client;
  User? _user;
  bool _isLoading = true;
  bool _hasProfileCompleted = false;

  @override
  void initState() {
    super.initState();
    _escutarAutenticacao();
  }

  void _escutarAutenticacao() {
    // Fica escutando mudanças de login/logout/registro em tempo real
    supabase.auth.onAuthStateChange.listen((data) async {
      final session = data.session;

      if (session != null) {
        _user = session.user;
        // Se está logado, verifica se o perfil dele já existe na tabela pública
        await _verificarPerfilExistente(session.user.id);
      } else {
        if (mounted) {
          setState(() {
            _user = null;
            _isLoading = false;
          });
        }
      }
    });
  }

  Future<void> _verificarPerfilExistente(String userId) async {
    if (!mounted) return;
    setState(() => _isLoading = true);

    try {
      final data = await supabase
          .from('profiles')
          .select('nome_completo')
          .eq('id', userId)
          .maybeSingle(); // Retorna null ou 1 registro

      if (data != null &&
          data['nome_completo'] != null &&
          data['nome_completo'].toString().trim().isNotEmpty) {
        setState(() => _hasProfileCompleted = true);
      } else {
        setState(() => _hasProfileCompleted = false);
      }
    } catch (e) {
      debugPrint('Erro no Gate ao verificar perfil: $e');
      setState(() => _hasProfileCompleted = false);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    // 1. Se estiver processando a resposta do banco de dados, mostra tela de carregamento
    if (_isLoading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    // 2. Se a usuária NÃO está logada, manda para a tela de Login
    if (_user == null) {
      return const LoginScreen();
    }

    // 3. Se está logada mas não completou o perfil, manda para o Onboarding
    if (!_hasProfileCompleted) {
      return OnboardingScreen(
        onComplete: () => _verificarPerfilExistente(_user!.id),
      );
    }

    // 4. Se passou em tudo, libera o aplicativo principal (Mapa e navegação)
    return const MainScreen();
  }
}
