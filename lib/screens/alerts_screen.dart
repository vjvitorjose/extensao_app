import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb; // Permite checar se é Web
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:geolocator/geolocator.dart';
import 'package:geocoding/geocoding.dart'; // Para Celulares
import 'package:http/http.dart' as http; // Para Navegador (Web)
import 'dart:convert';
import '../theme/app_colors.dart';

class AlertsScreen extends StatefulWidget {
  const AlertsScreen({super.key});

  @override
  State<AlertsScreen> createState() => _AlertsScreenState();
}

class _AlertsScreenState extends State<AlertsScreen> {
  final supabase = Supabase.instance.client;
  List<Map<String, dynamic>> _alertas = [];
  bool _carregando = true;
  String _erroMsg = '';

  @override
  void initState() {
    super.initState();
    _carregarAlertasProximos();
  }

  Future<void> _carregarAlertasProximos() async {
    try {
      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        setState(() => _erroMsg = 'Serviço de localização desativado.');
        return;
      }

      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
        if (permission == LocationPermission.denied) {
          setState(() => _erroMsg = 'Permissão de localização negada.');
          return;
        }
      }

      Position posicaoAtual = await Geolocator.getCurrentPosition();

      final resposta = await supabase
          .from('danger_reports')
          .select()
          .order('data_hora', ascending: false);

      List<Map<String, dynamic>> alertasFiltrados = [];

      for (var alerta in resposta) {
        double latAlerta = alerta['latitude'];
        double lngAlerta = alerta['longitude'];

        double distanciaEmMetros = Geolocator.distanceBetween(
          posicaoAtual.latitude,
          posicaoAtual.longitude,
          latAlerta,
          lngAlerta,
        );

        if (distanciaEmMetros <= 2000) {
          String enderecoFormatado = 'Endereço desconhecido';

          // --- INÍCIO DA LÓGICA HÍBRIDA ---
          try {
            if (kIsWeb) {
              // 1. SE FOR NAVEGADOR (WEB): Usa a API do OpenStreetMap
              final url = Uri.parse(
                'https://nominatim.openstreetmap.org/reverse?format=json&lat=$latAlerta&lon=$lngAlerta&zoom=18&addressdetails=1',
              );

              final response = await http.get(
                url,
                headers: {'User-Agent': 'SafeHerApp/1.0'},
              );

              if (response.statusCode == 200) {
                final data = json.decode(response.body);
                if (data != null && data['address'] != null) {
                  final address = data['address'];

                  String rua = address['road'] ?? address['pedestrian'] ?? '';
                  String bairro =
                      address['suburb'] ?? address['neighbourhood'] ?? '';

                  if (rua.isNotEmpty && bairro.isNotEmpty) {
                    enderecoFormatado = '$rua, $bairro';
                  } else if (rua.isNotEmpty) {
                    enderecoFormatado = rua;
                  }
                }
              }
            } else {
              // 2. SE FOR CELULAR (ANDROID/IOS): Usa os serviços nativos
              List<Placemark> placemarks = await placemarkFromCoordinates(
                latAlerta,
                lngAlerta,
              );
              if (placemarks.isNotEmpty) {
                Placemark place = placemarks[0];

                String rua = place.street ?? '';
                String bairro = place.subLocality ?? '';

                if (rua.isNotEmpty && bairro.isNotEmpty) {
                  enderecoFormatado = '$rua, $bairro';
                } else if (rua.isNotEmpty) {
                  enderecoFormatado = rua;
                }
              }
            }
          } catch (e) {
            debugPrint('Erro ao buscar endereço: $e');
          }
          // --- FIM DA LÓGICA HÍBRIDA ---

          alertasFiltrados.add({
            ...alerta,
            'distancia': distanciaEmMetros,
            'endereco': enderecoFormatado,
          });
        }
      }

      setState(() {
        _alertas = alertasFiltrados;
        _carregando = false;
      });
    } catch (e) {
      setState(() {
        _erroMsg = 'Erro ao carregar alertas: $e';
        _carregando = false;
      });
    }
  }

  Map<String, dynamic> _obterEstiloCategoria(String tipoBanco) {
    switch (tipoBanco) {
      case 'assedio':
        return {
          'label': 'Assédio',
          'bg': AppColors.riskAssedioBg,
          'text': AppColors.riskAssedioText,
        };
      case 'iluminacao_ruim':
        return {
          'label': 'Iluminação ruim',
          'bg': AppColors.riskIluminacaoBg,
          'text': AppColors.riskIluminacaoText,
        };
      case 'perseguicao':
        return {
          'label': 'Perseguição',
          'bg': AppColors.riskPerseguicaoBg,
          'text': AppColors.riskPerseguicaoText,
        };
      case 'area_deserta':
      default:
        return {
          'label': 'Local suspeito',
          'bg': AppColors.riskSuspeitoBg,
          'text': AppColors.riskSuspeitoText,
        };
    }
  }

  String _formatarDistancia(double metros) {
    if (metros < 1000) {
      return '${metros.toInt()} m de você';
    } else {
      return '${(metros / 1000).toStringAsFixed(1)} km de você';
    }
  }

  String _calcularTempoAtras(String dataString) {
    DateTime dataAlerta = DateTime.parse(dataString);
    Duration diferenca = DateTime.now().difference(dataAlerta);

    if (diferenca.inMinutes < 60) {
      return 'há ${diferenca.inMinutes} min';
    } else if (diferenca.inHours < 24) {
      return 'há ${diferenca.inHours} h';
    } else {
      return 'há ${diferenca.inDays} dias';
    }
  }

  Widget _buildAlertCard(Map<String, dynamic> alerta) {
    final estilo = _obterEstiloCategoria(alerta['tipo_perigo'] ?? '');
    final tempo = _calcularTempoAtras(alerta['data_hora']);
    final distancia = _formatarDistancia(alerta['distancia']);

    final descricao = alerta['descricao'] ?? 'Sem descrição detalhada.';
    final endereco = alerta['endereco'] ?? 'Endereço não encontrado';

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: Colors.grey.shade200),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 4,
                ),
                decoration: BoxDecoration(
                  color: estilo['bg'],
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  estilo['label'],
                  style: TextStyle(
                    color: estilo['text'],
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              Text(
                tempo,
                style: const TextStyle(fontSize: 11, color: Colors.grey),
              ),
            ],
          ),
          const SizedBox(height: 12),

          Text(
            endereco,
            style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
          ),

          const SizedBox(height: 4),
          Text(
            descricao,
            style: const TextStyle(fontSize: 13, color: Colors.black54),
          ),
          const SizedBox(height: 8),
          Text(
            distancia,
            style: const TextStyle(
              fontSize: 12,
              color: AppColors.primary,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey.shade50,
      appBar: AppBar(
        backgroundColor: AppColors.primary,
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Alertas próximos',
              style: TextStyle(fontSize: 18, color: Colors.white),
            ),
            Text(
              'Raio de 2 km da sua localização',
              style: TextStyle(fontSize: 12, color: Colors.white70),
            ),
          ],
        ),
      ),
      body: _carregando
          ? const Center(child: CircularProgressIndicator())
          : _erroMsg.isNotEmpty
          ? Center(
              child: Text(
                _erroMsg,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.red),
              ),
            )
          : _alertas.isEmpty
          ? const Center(
              child: Text(
                'Nenhum alerta em um raio de 2 km.',
                style: TextStyle(color: Colors.grey, fontSize: 16),
              ),
            )
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _alertas.length,
              itemBuilder: (context, index) {
                return _buildAlertCard(_alertas[index]);
              },
            ),
    );
  }
}
