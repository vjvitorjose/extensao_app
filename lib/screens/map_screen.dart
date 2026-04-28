import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import '../theme/app_colors.dart';
import '../widgets/risk_chip.dart';
import 'sos_screen.dart';

class MapScreen extends StatefulWidget {
  const MapScreen({super.key});

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  late GoogleMapController mapController;

  // Coordenadas centrais de São João del-Rei
  final LatLng _center = const LatLng(-21.1355, -44.2616);

  // Exemplo de um marcador de ocorrência
  final Set<Marker> _markers = {
    Marker(
      markerId: const MarkerId('risco_1'),
      position: const LatLng(-21.1350, -44.2610),
      infoWindow: const InfoWindow(title: 'Perseguição', snippet: 'há 12 min'),
      icon: BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueRed),
    ),
  };

  void _onMapCreated(GoogleMapController controller) {
    mapController = controller;
  }

  void _abrirModalRisco(BuildContext context) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      isScrollControlled: true,
      builder: (context) {
        return Padding(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(context).viewInsets.bottom,
            left: 20, right: 20, top: 20,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 36, height: 4,
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(color: Colors.grey[300], borderRadius: BorderRadius.circular(2)),
                ),
              ),
              const Text('Marcar local de risco', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              const SizedBox(height: 4),
              const Text('Sua localização atual', style: TextStyle(fontSize: 12, color: Colors.grey)),
              const SizedBox(height: 16),
              
              Wrap(
                spacing: 8, runSpacing: 8,
                children: const [
                  RiskChip(label: 'Assédio', bgColor: AppColors.riskAssedioBg, textColor: AppColors.riskAssedioText),
                  RiskChip(label: 'Iluminação ruim', bgColor: AppColors.riskIluminacaoBg, textColor: AppColors.riskIluminacaoText),
                  RiskChip(label: 'Perseguição', bgColor: AppColors.riskPerseguicaoBg, textColor: AppColors.riskPerseguicaoText),
                  RiskChip(label: 'Local suspeito', bgColor: AppColors.riskSuspeitoBg, textColor: AppColors.riskSuspeitoText),
                ],
              ),
              
              const SizedBox(height: 16),
              TextField(
                decoration: InputDecoration(
                  hintText: 'Descreva o ocorrido (opcional)...',
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                  contentPadding: const EdgeInsets.all(12),
                ),
                maxLines: 3,
              ),
              const SizedBox(height: 16),
              
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.primary,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  onPressed: () {
                    Navigator.pop(context);
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Risco registrado e autoridades notificadas!')),
                    );
                  },
                  child: const Text('Registrar e alertar autoridades', style: TextStyle(color: Colors.white)),
                ),
              ),
              const SizedBox(height: 20),
            ],
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: AppColors.primary,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: const [
            Text('SafeHer', style: TextStyle(fontSize: 18, color: Colors.white)),
            Text('São João del-Rei · 12 ocorrências esta semana', style: TextStyle(fontSize: 12, color: Colors.white70)),
          ],
        ),
      ),
      body: Stack(
        children: [
          GoogleMap(
            onMapCreated: _onMapCreated,
            initialCameraPosition: CameraPosition(
              target: _center,
              zoom: 15.0,
            ),
            markers: _markers,
            myLocationEnabled: true,
            myLocationButtonEnabled: false,
            zoomControlsEnabled: false,
          ),
          Positioned(
            bottom: 16,
            left: 16,
            child: InkWell(
              onTap: () {
                Navigator.push(context, MaterialPageRoute(builder: (_) => const SosScreen()));
              },
              child: Container(
                width: 64, height: 64,
                decoration: BoxDecoration(
                  color: AppColors.sosRed,
                  shape: BoxShape.circle,
                  border: Border.all(color: AppColors.sosRedBorder, width: 3),
                ),
                child: const Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.warning_amber_rounded, color: Colors.white, size: 20),
                    Text('SOS', style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold)),
                  ],
                ),
              ),
            ),
          ),
          Positioned(
            bottom: 24,
            right: 16,
            child: FloatingActionButton(
              heroTag: 'report_btn',
              backgroundColor: AppColors.primary,
              onPressed: () => _abrirModalRisco(context),
              child: const Icon(Icons.add_location_alt, color: Colors.white),
            ),
          ),
        ],
      ),
    );
  }
}