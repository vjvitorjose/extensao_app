import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../theme/app_colors.dart';

class AdminMapScreen extends StatefulWidget {
  const AdminMapScreen({super.key});

  @override
  State<AdminMapScreen> createState() => _AdminMapScreenState();
}

class _AdminMapScreenState extends State<AdminMapScreen> {
  final supabase = Supabase.instance.client;
  GoogleMapController? _mapController;
  Set<Marker> _markers = {};
  bool _carregando = true;
  String? _erro;
  int _totalAlertas = 0;

  static const _saoJoaoDelRei = LatLng(-21.1355, -44.2616);

  @override
  void initState() {
    super.initState();
    _carregarAlertas();
  }

  Future<void> _carregarAlertas() async {
    setState(() {
      _carregando = true;
      _erro = null;
    });

    try {
      final resposta = await supabase
          .from('danger_reports')
          .select('id, tipo_perigo, descricao, endereco, latitude, longitude, criado_em')
          .order('criado_em', ascending: false);

      final markers = <Marker>{};
      for (var index = 0; index < resposta.length; index++) {
        final alerta = Map<String, dynamic>.from(resposta[index]);
        final latitude = (alerta['latitude'] as num?)?.toDouble();
        final longitude = (alerta['longitude'] as num?)?.toDouble();
        if (latitude == null || longitude == null) continue;

        final tipo = alerta['tipo_perigo']?.toString() ?? 'Local suspeito';
        final descricao = alerta['descricao']?.toString() ?? 'Sem descrição';
        final endereco = alerta['endereco']?.toString() ?? 'Endereço não informado';
        final markerId = alerta['id']?.toString() ?? 'alerta-$index';
        markers.add(
          Marker(
            markerId: MarkerId(markerId),
            position: LatLng(latitude, longitude),
            icon: BitmapDescriptor.defaultMarkerWithHue(_hueParaTipo(tipo)),
            infoWindow: InfoWindow(
              title: _rotuloDoTipo(tipo),
              snippet: '$endereco | $descricao',
            ),
          ),
        );
      }

      if (!mounted) return;
      setState(() {
        _markers = markers;
        _totalAlertas = resposta.length;
        _carregando = false;
      });
      _ajustarCameraAosAlertas();
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _erro = 'Não foi possível carregar os alertas: $error';
        _carregando = false;
      });
    }
  }

  String _rotuloDoTipo(String tipo) {
    const labels = {
      'assedio': 'Assédio',
      'iluminacao_ruim': 'Iluminação ruim',
      'perseguicao': 'Perseguição',
      'area_deserta': 'Local suspeito',
      'acidente_transito': 'Acidente de trânsito',
      'assalto': 'Assalto',
      'furto': 'Furto',
      'violencia_fisica': 'Violência física',
      'presenca_arma': 'Presença de arma',
      'incendio': 'Incêndio ou fumaça',
      'via_bloqueada': 'Via bloqueada',
      'emergencia_medica': 'Emergência médica',
    };
    return labels[tipo] ?? tipo;
  }

  double _hueParaTipo(String tipo) {
    switch (tipo) {
      case 'assalto':
      case 'violencia_fisica':
      case 'presenca_arma':
        return BitmapDescriptor.hueRed;
      case 'acidente_transito':
      case 'incendio':
        return BitmapDescriptor.hueOrange;
      case 'emergencia_medica':
        return BitmapDescriptor.hueGreen;
      case 'via_bloqueada':
      case 'iluminacao_ruim':
        return BitmapDescriptor.hueYellow;
      default:
        return BitmapDescriptor.hueViolet;
    }
  }

  Future<void> _ajustarCameraAosAlertas() async {
    final controller = _mapController;
    if (controller == null || _markers.isEmpty) return;

    final positions = _markers.map((marker) => marker.position).toList();
    if (positions.length == 1) {
      await controller.animateCamera(
        CameraUpdate.newCameraPosition(
          CameraPosition(target: positions.first, zoom: 15),
        ),
      );
      return;
    }

    final bounds = LatLngBounds(
      southwest: LatLng(
        positions.map((position) => position.latitude).reduce((a, b) => a < b ? a : b),
        positions.map((position) => position.longitude).reduce((a, b) => a < b ? a : b),
      ),
      northeast: LatLng(
        positions.map((position) => position.latitude).reduce((a, b) => a > b ? a : b),
        positions.map((position) => position.longitude).reduce((a, b) => a > b ? a : b),
      ),
    );
    await controller.animateCamera(CameraUpdate.newLatLngBounds(bounds, 60));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        title: const Text('Painel administrativo'),
        actions: [
          IconButton(
            tooltip: 'Atualizar alertas',
            onPressed: _carregando ? null : _carregarAlertas,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: Stack(
        children: [
          GoogleMap(
            initialCameraPosition: const CameraPosition(
              target: _saoJoaoDelRei,
              zoom: 12,
            ),
            onMapCreated: (controller) {
              _mapController = controller;
              _ajustarCameraAosAlertas();
            },
            markers: _markers,
            myLocationButtonEnabled: false,
            zoomControlsEnabled: true,
          ),
          Positioned(
            top: 16,
            left: 16,
            right: 16,
            child: Card(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                child: Row(
                  children: [
                    const Icon(Icons.warning_amber_rounded, color: AppColors.sosRed),
                    const SizedBox(width: 10),
                    Text(
                      '$_totalAlertas alertas cadastrados',
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
              ),
            ),
          ),
          if (_carregando) const Center(child: CircularProgressIndicator()),
          if (_erro != null)
            Center(
              child: Card(
                margin: const EdgeInsets.all(24),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Text(_erro!),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
