import 'package:flutter/material.dart';
import 'theme/app_colors.dart';
import 'screens/main_screen.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

Future<void> main() async {
  // Garantir que o binding do Flutter está inicializado antes de carregar ficheiros
  WidgetsFlutterBinding.ensureInitialized();
  
  // Carregar o ficheiro .env
  await dotenv.load(fileName: ".env");

  runApp(const SafeHerApp());
}

class SafeHerApp extends StatelessWidget {
  const SafeHerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SafeHer',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        primaryColor: AppColors.primary,
        colorScheme: ColorScheme.fromSeed(
          seedColor: AppColors.primary,
          secondary: AppColors.sosRed,
        ),
        fontFamily: 'Roboto', 
      ),
      home: const MainScreen(),
    );
  }
}