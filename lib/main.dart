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
      onGenerateInitialRoutes: (initialRoute) {
        final uri = Uri.base;
        final path = uri.path.toLowerCase();
        final fragment = uri.fragment.toLowerCase();
        final isAdmin = path == '/adm' ||
            path == '/adm/' ||
            path.endsWith('/adm') ||
            path.endsWith('/adm/') ||
            fragment == '/adm' ||
            fragment == 'adm' ||
            fragment.endsWith('/adm') ||
            initialRoute == '/adm';

        if (isAdmin) {
          return [
            MaterialPageRoute(
              builder: (_) => const AdminMapScreen(),
              settings: const RouteSettings(name: '/adm'),
            ),
          ];
        }

        return [
          MaterialPageRoute(
            builder: (_) => const AuthGate(),
            settings: const RouteSettings(name: '/'),
          ),
        ];
      },
      onGenerateRoute: (settings) {
        if (settings.name == '/adm') {
          return MaterialPageRoute(
            builder: (_) => const AdminMapScreen(),
            settings: settings,
          );
        }
        return MaterialPageRoute(
          builder: (_) => const AuthGate(),
          settings: settings,
        );
      },
    );
  }
}

