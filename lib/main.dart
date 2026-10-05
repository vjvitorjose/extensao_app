import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_web_plugins/url_strategy.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:provider/provider.dart';
import 'theme/app_colors.dart';
import 'providers/auth_provider.dart';
import 'providers/user_profile_provider.dart';
import 'providers/app_settings_provider.dart';
import 'providers/map_provider.dart';
import 'screens/auth_gate.dart';

Future<void> main() async {
  usePathUrlStrategy();
  WidgetsFlutterBinding.ensureInitialized();
  await dotenv.load(fileName: ".env");

  await Supabase.initialize(
    url: dotenv.env['SUPABASE_URL']!,
    anonKey: dotenv.env['SUPABASE_ANON_KEY']!,
  );

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthProvider()..initialize()),
        ChangeNotifierProvider(create: (_) => UserProfileProvider()),
        ChangeNotifierProvider(create: (_) => AppSettingsProvider()..loadSettings()),
        ChangeNotifierProvider(create: (_) => MapProvider()),
      ],
      child: const VigIAApp(),
    ),
  );
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
        return [
          MaterialPageRoute(
            builder: (_) => const AuthGate(),
            settings: const RouteSettings(name: '/'),
          ),
        ];
      },
      onGenerateRoute: (settings) {
        return MaterialPageRoute(
          builder: (_) => const AuthGate(),
          settings: settings,
        );
      },
    );
  }
}
