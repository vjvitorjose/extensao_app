import 'dart:async';

import 'package:flutter/material.dart';
import '../services/local_audio_service.dart';
import '../theme/app_colors.dart';

class SosScreen extends StatefulWidget {
  const SosScreen({super.key});

  @override
  State<SosScreen> createState() => _SosScreenState();
}

class _SosScreenState extends State<SosScreen> {
  final LocalAudioService _audioService = LocalAudioService.instance;
  bool _isTriggered = false;
  bool _isRecording = false;
  String _statusText = 'Pressione para começar a gravação local do áudio.';
  String _storageLocation = '';
  Timer? _timer;
  int _elapsedSeconds = 0;

  @override
  void initState() {
    super.initState();
    _loadStorageLocation();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _loadStorageLocation() async {
    final location = await _audioService.getStorageLocationDescription();
    if (!mounted) return;
    setState(() => _storageLocation = location);
  }

  Future<void> _toggleRecording() async {
    if (_isRecording) {
      await _stopRecording();
      return;
    }

    final started = await _audioService.startRecording(
      locationLabel: 'SOS ativado em ${DateTime.now().toLocal().toString().split('.')[0]}',
    );

    if (!started) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Não foi possível iniciar a gravação. Verifique a permissão de microfone.')),
      );
      return;
    }

    if (!mounted) return;
    setState(() {
      _isTriggered = true;
      _isRecording = true;
      _statusText = 'Gravação local iniciada. O áudio fica apenas no seu dispositivo.';
      _elapsedSeconds = 0;
    });

    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) return;
      setState(() => _elapsedSeconds++);
    });
  }

  Future<void> _stopRecording() async {
    final recording = await _audioService.stopRecording();
    _timer?.cancel();

    if (!mounted) return;
    setState(() {
      _isRecording = false;
      _statusText = recording != null
          ? 'Gravação salva localmente no seu dispositivo.'
          : 'Gravação interrompida.';
      _elapsedSeconds = 0;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(recording != null
            ? 'Áudio gravado com sucesso no dispositivo.'
            : 'Nenhuma gravação foi salva.'),
      ),
    );
  }

  String _formatElapsedTime(int seconds) {
    final minutes = seconds ~/ 60;
    final remainingSeconds = seconds % 60;
    return '${minutes.toString().padLeft(2, '0')}:${remainingSeconds.toString().padLeft(2, '0')}';
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
                onTap: _toggleRecording,
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
                      Icon(
                        _isRecording ? Icons.stop_circle : Icons.notifications_active,
                        color: Colors.white,
                        size: 40,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        _isRecording ? 'PARAR' : (_isTriggered ? 'ATIVADO' : 'PRESSIONE'),
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
                _statusText,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 14, color: Colors.black54),
              ),
              const SizedBox(height: 8),
              if (_isRecording)
                Text(
                  'Tempo gravado: ${_formatElapsedTime(_elapsedSeconds)}',
                  style: const TextStyle(fontWeight: FontWeight.bold, color: AppColors.sosRed),
                ),
              const SizedBox(height: 8),
              Text(
                'Armazenamento local: $_storageLocation',
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 12, color: Colors.black54),
              ),
            ],
          ),
        ),
      ),
    );
  }
}