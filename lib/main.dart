import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'theme/app_colors.dart';
import 'screens/auth_gate.dart'; // <-- A importação mágica do nosso novo Guardião!
import 'screens/admin_map_screen.dart';

Future<void> main() async {
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
      initialRoute: Uri.base.path == '/adm' ? '/adm' : '/',
      routes: {
        '/': (context) => const AuthGate(),
        '/adm': (context) => const AdminMapScreen(),
      },
    );
  }
}
