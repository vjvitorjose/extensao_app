import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';
import 'package:shared_preferences/shared_preferences.dart';

class LocalRecording {
  LocalRecording({
    required this.id,
    required this.filePath,
    required this.fileName,
    required this.durationMs,
    required this.locationLabel,
    required this.createdAt,
    this.latitude,
    this.longitude,
  });

  final String id;
  final String filePath;
  final String fileName;
  final int durationMs;
  final String locationLabel;
  final String createdAt;
  final double? latitude;
  final double? longitude;

  Map<String, dynamic> toJson() => {
        'id': id,
        'filePath': filePath,
        'fileName': fileName,
        'durationMs': durationMs,
        'locationLabel': locationLabel,
        'createdAt': createdAt,
        'latitude': latitude,
        'longitude': longitude,
      };

  factory LocalRecording.fromJson(Map<String, dynamic> json) => LocalRecording(
        id: json['id'].toString(),
        filePath: json['filePath'].toString(),
        fileName: json['fileName'].toString(),
        durationMs: (json['durationMs'] as num).toInt(),
        locationLabel: json['locationLabel'].toString(),
        createdAt: json['createdAt'].toString(),
        latitude: json['latitude'] != null ? (json['latitude'] as num).toDouble() : null,
        longitude: json['longitude'] != null ? (json['longitude'] as num).toDouble() : null,
      );
}

class LocalAudioService {
  LocalAudioService._();

  static final LocalAudioService instance = LocalAudioService._();

  final AudioRecorder _audioRecorder = AudioRecorder();

  bool _isRecording = false;
  DateTime? _recordingStartedAt;
  String? _currentFilePath;
  String? _currentFileName;
  String? _currentLocationLabel;

  bool get isRecording => _isRecording;
  DateTime? get recordingStartedAt => _recordingStartedAt;

  Future<String> get storageDirectoryPath async {
    final dir = await getApplicationDocumentsDirectory();
    final targetDir = Directory('${dir.path}/audio_recordings');
    if (!await targetDir.exists()) {
      await targetDir.create(recursive: true);
    }
    return targetDir.path;
  }

  Future<String> getStorageLocationDescription() async {
    if (Platform.isAndroid) {
      return 'Android (Pasta Download > audio_recordings)';
    }
    if (Platform.isIOS) {
      return 'iOS (App Arquivos > Extensao App > audio_recordings)';
    }
    return 'Pasta de gravações: ${await storageDirectoryPath}';
  }

  Future<bool> requestMicrophonePermission() async {
    try {
      if (await _audioRecorder.hasPermission()) {
        return true;
      }
      return await _audioRecorder.hasPermission(request: true);
    } catch (e) {
      debugPrint('Erro ao solicitar permissão de microfone: $e');
      return false;
    }
  }

  Future<bool> startRecording({required String locationLabel}) async {
    if (_isRecording) {
      return false;
    }

    try {
      final hasPermission = await requestMicrophonePermission();
      if (!hasPermission) {
        debugPrint('Microfone: permissão negada');
        return false;
      }

      final storageDirPath = await storageDirectoryPath;
      final timestamp = DateTime.now().toIso8601String().replaceAll(':', '-');
      final fileName = 'gravacao_$timestamp.m4a';
      final filePath = '$storageDirPath/$fileName';

      await _audioRecorder.start(
        const RecordConfig(
          encoder: AudioEncoder.aacLc,
          bitRate: 128000,
          sampleRate: 44100,
        ),
        path: filePath,
      );

      _isRecording = true;
      _recordingStartedAt = DateTime.now();
      _currentFilePath = filePath;
      _currentFileName = fileName;
      _currentLocationLabel = locationLabel;

      debugPrint('Gravação iniciada com sucesso: $filePath');
      return true;
    } catch (e) {
      debugPrint('Erro ao iniciar gravação de áudio: $e');
      _isRecording = false;
      return false;
    }
  }

  Future<LocalRecording?> stopRecording() async {
    if (!_isRecording) {
      return null;
    }

    try {
      final recordedPath = await _audioRecorder.stop();
      debugPrint('Gravação parada: $recordedPath');

      final duration = _recordingStartedAt == null
          ? 0
          : DateTime.now().difference(_recordingStartedAt!).inMilliseconds;

      final filePath = _currentFilePath;
      final fileName = _currentFileName;
      final locationLabel = _currentLocationLabel ?? 'Localização indisponível';

      _isRecording = false;
      _recordingStartedAt = null;
      _currentFilePath = null;
      _currentFileName = null;
      _currentLocationLabel = null;

      if (filePath == null || fileName == null) {
        debugPrint('Erro: caminho ou nome do arquivo não encontrado');
        return null;
      }

      // Verifica se o arquivo foi criado e tem conteúdo
      final file = File(filePath);
      if (!await file.exists()) {
        debugPrint('Erro: arquivo não foi criado em $filePath');
        return null;
      }

      final fileSize = await file.length();
      debugPrint('Arquivo salvo: $filePath (${fileSize} bytes)');

      if (fileSize == 0) {
        debugPrint('Aviso: arquivo está vazio, microfone pode não ter permissão');
      }

      String finalSavedPath = filePath;

      // Copia para a pasta pública /storage/emulated/0/Download/audio_recordings no Android
      if (Platform.isAndroid) {
        try {
          final publicDownloadDir = Directory('/storage/emulated/0/Download/audio_recordings');
          if (!await publicDownloadDir.exists()) {
            await publicDownloadDir.create(recursive: true);
          }
          final targetPath = '${publicDownloadDir.path}/$fileName';
          final copiedFile = await file.copy(targetPath);
          finalSavedPath = copiedFile.path;
          debugPrint('Cópia salva com sucesso em Download: $finalSavedPath');
        } catch (e) {
          debugPrint('Não foi possível copiar para /storage/emulated/0/Download: $e');
        }
      }

      final recording = LocalRecording(
        id: DateTime.now().toIso8601String(),
        filePath: finalSavedPath,
        fileName: fileName,
        durationMs: duration,
        locationLabel: locationLabel,
        createdAt: DateTime.now().toIso8601String(),
      );

      await _persistRecording(recording);
      return recording;
    } catch (e) {
      debugPrint('Erro ao parar gravação: $e');
      _isRecording = false;
      return null;
    }
  }

  Future<List<LocalRecording>> loadRecordings() async {
    final prefs = await SharedPreferences.getInstance();
    final rawItems = prefs.getStringList('local_recordings') ?? <String>[];

    final recordings = rawItems
        .map((item) => LocalRecording.fromJson(jsonDecode(item)))
        .toList();

    recordings.sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return recordings;
  }

  Future<void> deleteRecording(LocalRecording recording) async {
    final file = File(recording.filePath);
    if (await file.exists()) {
      await file.delete();
    }

    final prefs = await SharedPreferences.getInstance();
    final rawItems = prefs.getStringList('local_recordings') ?? <String>[];
    final remainingItems = rawItems.where((item) {
      final decoded = jsonDecode(item);
      return decoded['id'] != recording.id;
    }).toList();

    await prefs.setStringList('local_recordings', remainingItems);
  }

  Future<void> _persistRecording(LocalRecording recording) async {
    final prefs = await SharedPreferences.getInstance();
    final rawItems = prefs.getStringList('local_recordings') ?? <String>[];
    rawItems.add(jsonEncode(recording.toJson()));
    await prefs.setStringList('local_recordings', rawItems);
  }
}
