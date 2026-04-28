import 'package:flutter/material.dart';
import '../theme/app_colors.dart';

class SosScreen extends StatefulWidget {
  const SosScreen({super.key});

  @override
  State<SosScreen> createState() => _SosScreenState();
}

class _SosScreenState extends State<SosScreen> {
  bool _isTriggered = false;

  void _triggerSos() {
    if (_isTriggered) return;
    setState(() {
      _isTriggered = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.sosBackground,
      appBar: AppBar(
        backgroundColor: AppColors.sosRed,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: const [
            Text('Emergência SOS', style: TextStyle(fontSize: 18, color: Colors.white)),
            Text('Guarda Municipal · Polícia Militar', style: TextStyle(fontSize: 12, color: Colors.white70)),
          ],
        ),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.white),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              GestureDetector(
                onTap: _triggerSos,
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  width: _isTriggered ? 130 : 140,
                  height: _isTriggered ? 130 : 140,
                  decoration: BoxDecoration(
                    color: AppColors.sosRed,
                    shape: BoxShape.circle,
                    border: Border.all(color: AppColors.sosRedBorder, width: 6),
                  ),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.notifications_active, color: Colors.white, size: 40),
                      const SizedBox(height: 4),
                      Text(
                        _isTriggered ? 'ATIVADO' : 'PRESSIONE',
                        style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),
              Text(
                _isTriggered ? 'SOS ativado!' : 'Botão de pânico',
                style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: AppColors.sosRed),
              ),
              const SizedBox(height: 8),
              Text(
                _isTriggered 
                  ? 'Sua localização foi enviada para as autoridades e contatos.'
                  : 'Pressione para enviar seu GPS para as autoridades e contatos de emergência',
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 14, color: Colors.black54),
              ),
            ],
          ),
        ),
      ),
    );
  }
}