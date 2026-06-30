import 'package:flutter/material.dart';
import '../services/local_audio_service.dart';
import '../theme/app_colors.dart';

class RecordingsScreen extends StatefulWidget {
  const RecordingsScreen({super.key});

  @override
  State<RecordingsScreen> createState() => _RecordingsScreenState();
}

class _RecordingsScreenState extends State<RecordingsScreen> {
  final LocalAudioService _audioService = LocalAudioService.instance;
  List<LocalRecording> _recordings = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadRecordings();
  }

  Future<void> _loadRecordings() async {
    setState(() => _isLoading = true);
    final recordings = await _audioService.loadRecordings();
    if (!mounted) return;
    setState(() {
      _recordings = recordings;
      _isLoading = false;
    });
  }

  Future<void> _deleteRecording(LocalRecording recording) async {
    await _audioService.deleteRecording(recording);
    await _loadRecordings();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Gravação excluída do dispositivo.')),
    );
  }

  String _formatDuration(int milliseconds) {
    final seconds = (milliseconds / 1000).round();
    final minutes = seconds ~/ 60;
    final remainingSeconds = seconds % 60;
    return '$minutes:${remainingSeconds.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: AppColors.primary,
        title: const Text('Gravações', style: TextStyle(color: Colors.white)),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _recordings.isEmpty
              ? const Center(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Text(
                      'Nenhuma gravação local ainda.',
                      textAlign: TextAlign.center,
                      style: TextStyle(fontSize: 16, color: Colors.black54),
                    ),
                  ),
                )
              : ListView.separated(
                  itemCount: _recordings.length,
                  separatorBuilder: (_, __) => const Divider(height: 1),
                  itemBuilder: (context, index) {
                    final recording = _recordings[index];
                    return ListTile(
                      leading: const Icon(Icons.mic, color: AppColors.primary),
                      title: Text(recording.fileName),
                      subtitle: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Duração: ${_formatDuration(recording.durationMs)}'),
                          Text('Local: ${recording.locationLabel}'),
                          Text('Salvo em: ${recording.filePath}'),
                        ],
                      ),
                      trailing: IconButton(
                        icon: const Icon(Icons.delete_outline, color: Colors.red),
                        onPressed: () => _deleteRecording(recording),
                      ),
                    );
                  },
                ),
    );
  }
}
