import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import '../theme/app_colors.dart';
import '../widgets/admin_drawer.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final supabase = Supabase.instance.client;
  bool _isLoading = true;
  String? _error;
  
  // Data
  List<Map<String, dynamic>> _allReports = [];
  List<Map<String, dynamic>> _filteredReports = [];

  // Filters
  int _periodoDias = 30; // 7, 30, 365
  String? _tipoPerigo;
  String? _nivelRisco;
  bool _focoMulher = false;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final response = await supabase.from('danger_reports').select();
      if (mounted) {
        setState(() {
          _allReports = List<Map<String, dynamic>>.from(response);
          _applyFilters();
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = 'Erro ao carregar dados: $e';
          _isLoading = false;
        });
      }
    }
  }

  void _applyFilters() {
    final now = DateTime.now();
    final cutoffDate = now.subtract(Duration(days: _periodoDias));

    _filteredReports = _allReports.where((report) {
      final createdAtStr = report['created_at'] ?? report['criado_em'];
      if (createdAtStr == null) return false;
      final createdAt = DateTime.tryParse(createdAtStr.toString());
      if (createdAt == null) return false;

      // Filter Period
      if (createdAt.isBefore(cutoffDate)) return false;

      // Filter Foco Mulher
      final tipo = report['tipo_perigo']?.toString() ?? '';
      if (_focoMulher && !['assedio', 'perseguicao', 'violencia_fisica'].contains(tipo)) {
        return false;
      }

      // Filter Tipo
      if (_tipoPerigo != null && _tipoPerigo != 'Todos' && tipo != _tipoPerigo) {
        return false;
      }

      // Filter Risco
      final risco = report['nivel_risco']?.toString().toLowerCase() ?? '';
      if (_nivelRisco != null && _nivelRisco != 'Todos' && risco != _nivelRisco?.toLowerCase()) {
        return false;
      }

      return true;
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      drawer: const AdminDrawer(),
      appBar: AppBar(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        title: const Text('Dashboard Analítico'),
        actions: [
          IconButton(
            tooltip: 'Atualizar dados',
            icon: const Icon(Icons.refresh),
            onPressed: _loadData,
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) return const Center(child: CircularProgressIndicator());
    if (_error != null) return _buildError();
    
    return RefreshIndicator(
      onRefresh: _loadData,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildFiltersBar(),
              const SizedBox(height: 16),
              _buildIndicators(),
              const SizedBox(height: 24),
              _buildMapAndRanking(),
              const SizedBox(height: 24),
              _buildEvolutionCharts(),
              const SizedBox(height: 24),
              _buildTypeAndRiskCharts(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildError() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, color: Colors.red, size: 48),
            const SizedBox(height: 16),
            Text(_error!, textAlign: TextAlign.center, style: const TextStyle(color: Colors.red)),
            const SizedBox(height: 16),
            ElevatedButton(onPressed: _loadData, child: const Text('Tentar Novamente')),
          ],
        ),
      ),
    );
  }

  Widget _buildFiltersBar() {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
        child: Wrap(
          spacing: 16,
          runSpacing: 16,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            // Periodo
            DropdownButton<int>(
              value: _periodoDias,
              underline: const SizedBox(),
              items: const [
                DropdownMenuItem(value: 7, child: Text('Últimos 7 dias')),
                DropdownMenuItem(value: 30, child: Text('Últimos 30 dias')),
                DropdownMenuItem(value: 365, child: Text('Último ano')),
              ],
              onChanged: (val) {
                if (val != null) setState(() { _periodoDias = val; _applyFilters(); });
              },
            ),
            // Tipo
            DropdownButton<String>(
              value: _tipoPerigo ?? 'Todos',
              underline: const SizedBox(),
              items: ['Todos', 'assedio', 'perseguicao', 'violencia_fisica', 'assalto', 'furto', 'area_deserta', 'iluminacao_ruim', 'acidente_transito']
                  .map((t) => DropdownMenuItem(value: t, child: Text(t == 'Todos' ? 'Todos os Tipos' : _formatTypeLabel(t))))
                  .toList(),
              onChanged: (val) {
                setState(() { _tipoPerigo = val == 'Todos' ? null : val; _applyFilters(); });
              },
            ),
            // Risco
            DropdownButton<String>(
              value: _nivelRisco ?? 'Todos',
              underline: const SizedBox(),
              items: const [
                DropdownMenuItem(value: 'Todos', child: Text('Todos os Riscos')),
                DropdownMenuItem(value: 'Alto', child: Text('Alto')),
                DropdownMenuItem(value: 'Medio', child: Text('Médio')),
                DropdownMenuItem(value: 'Baixo', child: Text('Baixo')),
              ],
              onChanged: (val) {
                setState(() { _nivelRisco = val == 'Todos' ? null : val; _applyFilters(); });
              },
            ),
            // Foco Mulher
            FilterChip(
              label: const Text('Foco Mulher'),
              selected: _focoMulher,
              selectedColor: Colors.pink.shade100,
              checkmarkColor: Colors.pink,
              onSelected: (val) {
                setState(() { _focoMulher = val; _applyFilters(); });
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildIndicators() {
    int total = _filteredReports.length;
    int altoRisco = _filteredReports.where((r) => r['nivel_risco']?.toString().toLowerCase() == 'alto').length;
    
    final now = DateTime.now();
    final last7 = _filteredReports.where((r) {
      final dStr = r['created_at'] ?? r['criado_em'];
      if (dStr == null) return false;
      final d = DateTime.tryParse(dStr);
      if (d == null) return false;
      return d.isAfter(now.subtract(const Duration(days: 7)));
    }).length;

    // TODO: Ajustar lógica de pendentes quando campo existir. Usando 0 para layout.
    int pendentes = 0; 

    return LayoutBuilder(
      builder: (context, constraints) {
        double width = (constraints.maxWidth - 3 * 16) / 4;
        if (constraints.maxWidth < 600) width = (constraints.maxWidth - 16) / 2; // 2 cols on mobile
        
        return Wrap(
          spacing: 16,
          runSpacing: 16,
          children: [
            SizedBox(width: width, child: _buildStatCard('Total Período', total.toString(), Icons.analytics, Colors.blue)),
            SizedBox(width: width, child: _buildStatCard('Alto Risco', altoRisco.toString(), Icons.warning_amber, Colors.red)),
            SizedBox(width: width, child: _buildStatCard('Últimos 7 dias', last7.toString(), Icons.trending_up, Colors.orange)),
            SizedBox(width: width, child: _buildStatCard('Pendentes', pendentes.toString(), Icons.pending_actions, Colors.grey)),
          ],
        );
      },
    );
  }

  Widget _buildMapAndRanking() {
    // Map Markers
    Set<Marker> markers = _filteredReports.map((r) {
      final lat = r['latitude'];
      final lng = r['longitude'];
      final risco = r['nivel_risco']?.toString().toLowerCase();
      
      double hue = BitmapDescriptor.hueRed;
      if (risco == 'baixo') hue = BitmapDescriptor.hueGreen;
      if (risco == 'medio') hue = BitmapDescriptor.hueOrange;

      if (lat != null && lng != null) {
        return Marker(
          markerId: MarkerId(r['id']?.toString() ?? UniqueKey().toString()),
          position: LatLng(lat, lng),
          icon: BitmapDescriptor.defaultMarkerWithHue(hue),
          infoWindow: InfoWindow(title: _formatTypeLabel(r['tipo_perigo']?.toString() ?? '')),
        );
      }
      return null;
    }).where((m) => m != null).cast<Marker>().toSet();

    // Ranking Logic (naive grouping by address/region string)
    Map<String, int> regionsCount = {};
    for (var r in _filteredReports) {
      String rawEndereco = r['endereco']?.toString() ?? '';
      String region = 'Desconhecida';
      if (rawEndereco.isNotEmpty) {
        // Try to get neighborhood (often after a comma)
        final parts = rawEndereco.split(',');
        if (parts.length > 1 && parts[1].trim() != 'MG') {
            region = parts[1].trim();
        } else {
            region = parts[0].trim();
        }
      } else {
         final lat = r['latitude'] as double?;
         final lng = r['longitude'] as double?;
         if (lat != null && lng != null) {
           region = 'Região Aprox (${lat.toStringAsFixed(2)}, ${lng.toStringAsFixed(2)})';
         }
      }
      if (region.isEmpty || region == 'São João del-Rei') region = 'Área Central';
      regionsCount[region] = (regionsCount[region] ?? 0) + 1;
    }

    var sortedRegions = regionsCount.entries.toList()..sort((a, b) => b.value.compareTo(a.value));
    var top5 = sortedRegions.take(5).toList();

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Mapa (2/3 approx, or full width if mobile, handled simply here as Row for web/tablet)
        Expanded(
          flex: 2,
          child: Card(
            elevation: 2,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: SizedBox(
                height: 400,
                child: GoogleMap(
                  initialCameraPosition: const CameraPosition(
                    target: LatLng(-21.135, -44.261), // SJDR
                    zoom: 13,
                  ),
                  markers: markers,
                  myLocationButtonEnabled: false,
                ),
              ),
            ),
          ),
        ),
        const SizedBox(width: 16),
        // Ranking (1/3)
        Expanded(
          flex: 1,
          child: Card(
            elevation: 2,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            child: Container(
              height: 400,
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Regiões Mais Críticas', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  const Divider(),
                  Expanded(
                    child: top5.isEmpty 
                      ? const Center(child: Text('Nenhum dado'))
                      : ListView.builder(
                          itemCount: top5.length,
                          itemBuilder: (ctx, i) {
                            return ListTile(
                              contentPadding: EdgeInsets.zero,
                              leading: CircleAvatar(backgroundColor: Colors.red.shade100, child: Text('${i+1}')),
                              title: Text(top5[i].key, maxLines: 1, overflow: TextOverflow.ellipsis),
                              trailing: Text('${top5[i].value}', style: const TextStyle(fontWeight: FontWeight.bold)),
                            );
                          },
                        ),
                  ),
                ],
              ),
            ),
          ),
        )
      ],
    );
  }

  Widget _buildEvolutionCharts() {
    // 1. Linha do Tempo (Últimos dias selecionados)
    Map<String, int> reportsByDate = {};
    for (var r in _filteredReports) {
      final dtStr = r['created_at'] ?? r['criado_em'];
      if (dtStr != null) {
        final dt = DateTime.tryParse(dtStr);
        if (dt != null) {
          final dateKey = '${dt.year}-${dt.month.toString().padLeft(2,'0')}-${dt.day.toString().padLeft(2,'0')}';
          reportsByDate[dateKey] = (reportsByDate[dateKey] ?? 0) + 1;
        }
      }
    }
    var sortedDates = reportsByDate.keys.toList()..sort();
    
    // 2. Horários
    List<int> reportsByHour = List.filled(24, 0);
    for (var r in _filteredReports) {
      final dtStr = r['created_at'] ?? r['criado_em'];
      if (dtStr != null) {
        final dt = DateTime.tryParse(dtStr);
        if (dt != null) {
          reportsByHour[dt.hour]++;
        }
      }
    }

    return Row(
      children: [
        // Evolucao temporal
        Expanded(
          child: Card(
            elevation: 2,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Relatos ao Longo do Tempo', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  const SizedBox(height: 16),
                  SizedBox(
                    height: 250,
                    child: sortedDates.isEmpty ? const Center(child: Text('Nenhum dado')) : _buildTimeLineChart(sortedDates, reportsByDate),
                  )
                ],
              ),
            ),
          ),
        ),
        const SizedBox(width: 16),
        // Horários
        Expanded(
          child: Card(
            elevation: 2,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Distribuição por Horário (0h - 23h)', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  const SizedBox(height: 16),
                  SizedBox(
                    height: 250,
                    child: _filteredReports.isEmpty ? const Center(child: Text('Nenhum dado')) : _buildHourBarChart(reportsByHour),
                  )
                ],
              ),
            ),
          ),
        )
      ],
    );
  }

  Widget _buildTypeAndRiskCharts() {
    // 1. Tipos (Horizontal bar logic)
    Map<String, int> typeCounts = {};
    for (var r in _filteredReports) {
      String t = r['tipo_perigo']?.toString() ?? 'Desconhecido';
      typeCounts[t] = (typeCounts[t] ?? 0) + 1;
    }
    var sortedTypes = typeCounts.entries.toList()..sort((a,b) => b.value.compareTo(a.value));
    int maxTypeCount = sortedTypes.isNotEmpty ? sortedTypes.first.value : 1;

    // 2. Niveis (Vertical Alto, Medio, Baixo)
    Map<String, int> riskCounts = {'alto': 0, 'medio': 0, 'baixo': 0};
    for (var r in _filteredReports) {
      String rl = r['nivel_risco']?.toString().toLowerCase() ?? 'desconhecido';
      if (riskCounts.containsKey(rl)) {
        riskCounts[rl] = riskCounts[rl]! + 1;
      }
    }

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Tipos (Horizontal)
        Expanded(
          child: Card(
            elevation: 2,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Relatos por Tipo de Perigo', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  const SizedBox(height: 16),
                  SizedBox(
                    height: 300,
                    child: sortedTypes.isEmpty ? const Center(child: Text('Nenhum dado')) : ListView.builder(
                      itemCount: sortedTypes.length,
                      itemBuilder: (ctx, i) {
                        final widthFactor = sortedTypes[i].value / maxTypeCount;
                        return Padding(
                          padding: const EdgeInsets.symmetric(vertical: 8.0),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(_formatTypeLabel(sortedTypes[i].key)),
                              const SizedBox(height: 4),
                              Row(
                                children: [
                                  Expanded(
                                    child: LayoutBuilder(builder: (context, constraints) {
                                      return Row(
                                        children: [
                                          Container(
                                            height: 20,
                                            width: constraints.maxWidth * widthFactor,
                                            decoration: BoxDecoration(
                                              color: AppColors.primary.withValues(alpha: 0.8),
                                              borderRadius: BorderRadius.circular(4)
                                            ),
                                          ),
                                        ],
                                      );
                                    }),
                                  ),
                                  const SizedBox(width: 8),
                                  Text('${sortedTypes[i].value}', style: const TextStyle(fontWeight: FontWeight.bold)),
                                ],
                              )
                            ],
                          ),
                        );
                      }
                    ),
                  )
                ],
              ),
            ),
          ),
        ),
        const SizedBox(width: 16),
        // Riscos
        Expanded(
          child: Card(
            elevation: 2,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Relatos por Nível de Risco', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  const SizedBox(height: 16),
                  SizedBox(
                    height: 300,
                    child: _buildRiskBarChart(riskCounts),
                  )
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }

  // --- Chart Helpers ---

  Widget _buildTimeLineChart(List<String> dates, Map<String, int> counts) {
    if (dates.length > 30) {
      // Simplifica para evitar muitos pontos. (Neste MVP apenas limitamos para plotar)
      dates = dates.sublist(dates.length - 30);
    }
    
    List<FlSpot> spots = [];
    for (int i = 0; i < dates.length; i++) {
      spots.add(FlSpot(i.toDouble(), counts[dates[i]]!.toDouble()));
    }

    return LineChart(
      LineChartData(
        minY: 0,
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            preventCurveOverShooting: true,
            color: AppColors.primary,
            barWidth: 3,
            isStrokeCapRound: true,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(show: true, color: AppColors.primary.withValues(alpha: 0.2)),
          ),
        ],
        titlesData: FlTitlesData(
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              getTitlesWidget: (value, meta) {
                int i = value.toInt();
                if (i >= 0 && i < dates.length) {
                  final d = dates[i].split('-');
                  // Se tiver muitos pontos, mostra a cada 5
                  if (dates.length > 10 && i % 5 != 0) return const SizedBox();
                  return Padding(
                    padding: const EdgeInsets.only(top: 8.0),
                    child: Text('${d[2]}/${d[1]}', style: const TextStyle(fontSize: 10)),
                  );
                }
                return const SizedBox();
              },
            ),
          ),
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
        gridData: const FlGridData(show: true, drawVerticalLine: false),
        borderData: FlBorderData(show: false),
      )
    );
  }

  Widget _buildHourBarChart(List<int> hoursCount) {
    List<BarChartGroupData> groups = [];
    for (int i = 0; i < 24; i++) {
      groups.add(BarChartGroupData(
        x: i,
        barRods: [
          BarChartRodData(
            toY: hoursCount[i].toDouble(),
            color: Colors.blueGrey,
            width: 10,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(4))
          )
        ]
      ));
    }

    return BarChart(
      BarChartData(
        barGroups: groups,
        titlesData: FlTitlesData(
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              interval: 3,
              getTitlesWidget: (value, meta) {
                return Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text('${value.toInt()}h', style: const TextStyle(fontSize: 10)),
                );
              }
            )
          ),
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
        gridData: const FlGridData(show: false),
        borderData: FlBorderData(show: false),
      )
    );
  }

  Widget _buildRiskBarChart(Map<String, int> riskCounts) {
    // Ordem pedida: Alto, Médio, Baixo
    final order = ['alto', 'medio', 'baixo'];
    final colors = [Colors.red, Colors.orange, Colors.green];
    final labels = ['Alto', 'Médio', 'Baixo'];

    final maxValue = riskCounts.values.fold<int>(0, (max, v) => v > max ? v : max);
    final topY = (maxValue > 0 ? maxValue * 1.2 : 10).toDouble();

    List<BarChartGroupData> groups = [];
    for (int i = 0; i < 3; i++) {
      final key = order[i];
      final val = riskCounts[key] ?? 0;
      groups.add(BarChartGroupData(
        x: i,
        showingTooltipIndicators: [0],
        barRods: [
          BarChartRodData(
            toY: val.toDouble(),
            color: colors[i],
            width: 40,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(6))
          )
        ]
      ));
    }

    return BarChart(
      BarChartData(
        maxY: topY,
        alignment: BarChartAlignment.spaceAround,
        barGroups: groups,
        barTouchData: BarTouchData(
          enabled: false,
          touchTooltipData: BarTouchTooltipData(
            // Use property instead of standard constructor for background if needed, but in newer fl_chart getTooltipColor is standard
            getTooltipColor: (group) => Colors.transparent,
            tooltipPadding: EdgeInsets.zero,
            tooltipMargin: 8,
            getTooltipItem: (group, groupIndex, rod, rodIndex) {
              return BarTooltipItem(
                rod.toY.round().toString(),
                const TextStyle(color: Colors.black, fontWeight: FontWeight.bold, fontSize: 16),
              );
            },
          ),
        ),
        titlesData: FlTitlesData(
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              getTitlesWidget: (value, meta) {
                return Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(labels[value.toInt()], style: const TextStyle(fontWeight: FontWeight.bold)),
                );
              }
            )
          ),
          leftTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
        gridData: const FlGridData(show: false),
        borderData: FlBorderData(show: false),
      )
    );
  }

  Widget _buildStatCard(String title, String value, IconData icon, Color color) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: color, size: 32),
            const SizedBox(height: 12),
            Text(value, style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text(title, textAlign: TextAlign.center, style: const TextStyle(fontSize: 14, color: Colors.grey)),
          ],
        ),
      ),
    );
  }

  String _formatTypeLabel(String tipo) {
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
    return labels[tipo] ?? tipo.replaceAll('_', ' ');
  }
}
