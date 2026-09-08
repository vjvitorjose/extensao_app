import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_web_plugins/url_strategy.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'theme/app_colors.dart';
import 'screens/auth_gate.dart';
import 'screens/admin_map_screen.dart';

Future<void> main() async {
  usePathUrlStrategy();
  WidgetsFlutterBinding.ensureInitialized();
  await dotenv.load(fileName: ".env");

  await Supabase.initialize(
    url: dotenv.env['SUPABASE_URL']!,
    anonKey: dotenv.env['SUPABASE_ANON_KEY']!,
  );

  runApp(const VigIAApp());
}

class VigIAApp extends StatelessWidget {
  const VigIAApp({super.key});

  static bool get _isAdminRoute {
    final path = Uri.base.path.toLowerCase();
    final fragment = Uri.base.fragment.toLowerCase();
    return path == '/adm' ||
        path == '/adm/' ||
        path.endsWith('/adm') ||
        path.endsWith('/adm/') ||
        fragment == '/adm' ||
        fragment == 'adm' ||
        fragment.endsWith('/adm');
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'vigIA',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        primaryColor: AppColors.primary,
        colorScheme: ColorScheme.fromSeed(
          seedColor: AppColors.primary,
          secondary: AppColors.sosRed,
        ),
        fontFamily: 'Roboto',
      ),
      initialRoute: _isAdminRoute ? '/adm' : '/',
      routes: {
        '/': (context) => const AuthGate(),
        '/adm': (context) => const AdminMapScreen(),
      },
    );
  }
}

