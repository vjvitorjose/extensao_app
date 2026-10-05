import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_map_heatmap/flutter_map_heatmap.dart';
import 'package:latlong2/latlong.dart';

class WebHeatmapMap extends StatelessWidget {
  final List<Map<String, dynamic>> reports;

  double _pesoPorRisco(dynamic nivelRisco) {
    final risco = nivelRisco?.toString().toLowerCase() ?? '';
    if (risco == 'alto') return 1.0;
    if (risco == 'medio') return 0.6;
    if (risco == 'baixo') return 0.3;
    return 0.5;
  }

  const WebHeatmapMap({super.key, required this.reports});

  @override
  Widget build(BuildContext context) {
    final heatmapData = <WeightedLatLng>[];
    for (var r in reports) {
      final lat = r['latitude'];
      final lng = r['longitude'];
      double? latDouble;
      double? lngDouble;
      if (lat is num) {
        latDouble = lat.toDouble();
      } else if (lat is String) {
        latDouble = double.tryParse(lat);
      }
      if (lng is num) {
        lngDouble = lng.toDouble();
      } else if (lng is String) {
        lngDouble = double.tryParse(lng);
      }
      if (latDouble != null && lngDouble != null) {
        heatmapData.add(
          WeightedLatLng(LatLng(latDouble, lngDouble), _pesoPorRisco(r['nivel_risco'])),
        );
      }
    }
    return FlutterMap(
      options: const MapOptions(
        initialCenter: LatLng(-21.135, -44.261),
        initialZoom: 13,
      ),
      children: [
        TileLayer(
          urlTemplate: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
          subdomains: const ['a', 'b', 'c'],
        ),
        if (heatmapData.isNotEmpty)
          HeatMapLayer(
            heatMapDataSource: InMemoryHeatMapDataSource(data: heatmapData),
            heatMapOptions: HeatMapOptions(
              radius: 30,
              blurFactor: 0.2,
              gradient: HeatMapOptions.defaultGradient,
            ),
          ),
      ],
    );
  }
}
