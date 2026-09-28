import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../providers/user_profile_provider.dart';
import 'login_screen.dart';
import 'main_screen.dart';
import 'onboarding_screen.dart';
import 'admin_map_screen.dart';

class AuthGate extends StatelessWidget {
  const AuthGate({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<AuthProvider>(
      builder: (context, auth, _) {
        // 1. Se estiver processando a resposta do banco de dados, mostra tela de carregamento
        if (auth.isLoading) {
          return const Scaffold(body: Center(child: CircularProgressIndicator()));
        }

        // 2. Se a usuária NÃO está logada, manda para a tela de Login
        if (!auth.isLoggedIn) {
          return const LoginScreen();
        }

        // 3. Se é admin, vai direto pro painel administrativo
        if (auth.isAdmin) {
          return const AdminMapScreen();
        }

        // 4. Se está logada mas não completou o perfil, manda para o Onboarding
        if (!auth.hasProfileCompleted) {
          return OnboardingScreen(
            onComplete: () => auth.refreshProfileStatus(),
          );
        }

        // 5. Se passou em tudo, libera o aplicativo principal (Mapa e navegação)
        // Carrega o perfil do usuário ao entrar no MainScreen
        context.read<UserProfileProvider>().loadProfile();
        return const MainScreen();
      },
    );
  }
}
