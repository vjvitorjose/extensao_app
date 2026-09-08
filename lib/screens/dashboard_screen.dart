import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
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
  Map<String, dynamic>? _stats;

  @override
  void initState() {
    super.initState();
    _loadStats();
  }

  Future<void> _loadStats() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final response = await supabase.rpc('get_dashboard_stats');
      if (mounted) {
        setState(() {
          _stats = response as Map<String, dynamic>;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = 'Erro ao carregar dashboard: $e\nLembre-se de rodar a migração SQL no Supabase.';
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      drawer: const AdminDrawer(),
      appBar: AppBar(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        title: const Text('Dashboard'),
        actions: [
          IconButton(
            tooltip: 'Atualizar dados',
            icon: const Icon(Icons.refresh),
            onPressed: _loadStats,
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
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
              ElevatedButton(
                onPressed: _loadStats,
                child: const Text('Tentar Novamente'),
              ),
            ],
          ),
        ),
      );
    }

    if (_stats == null) {
      return const Center(child: Text('Nenhum dado disponível.'));
    }

    final totalUsers = _stats!['total_users'] ?? 0;
    final activeAlerts = _stats!['active_alerts'] ?? 0;
    final pendingReports = _stats!['pending_reports'] ?? 0;
    final recurringVictimsCount = _stats!['recurring_victims_count'] ?? 0;
    final reportsByType = List<Map<String, dynamic>>.from(_stats!['reports_by_type'] ?? []);
    final reportsByRisk = List<Map<String, dynamic>>.from(_stats!['reports_by_risk'] ?? []);
    final alertsByDate = List<Map<String, dynamic>>.from(_stats!['alerts_by_date'] ?? []);

    return RefreshIndicator(
      onRefresh: _loadStats,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Visão Geral',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            GridView.count(
              crossAxisCount: 2,
              crossAxisSpacing: 16,
              mainAxisSpacing: 16,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              childAspectRatio: 1.3,
              children: [
                _buildStatCard('Usuários', totalUsers.toString(), Icons.people, Colors.blue),
                _buildStatCard('Alertas Ativos', activeAlerts.toString(), Icons.warning, Colors.red),
                _buildStatCard('Relatos Pendentes', pendingReports.toString(), Icons.report_problem, Colors.orange),
                _buildStatCard('Vítimas Recorrentes', recurringVictimsCount.toString(), Icons.repeat, Colors.purple),
              ],
            ),
            const SizedBox(height: 32),

            // GRÁFICO DE PIZZA (TIPOS)
            const Text(
              'Relatos por Tipo de Perigo',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            if (reportsByType.isEmpty)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(16.0),
                  child: Text('Nenhum relato de perigo registrado ainda.'),
                ),
              )
            else
              Card(
                elevation: 2,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: SizedBox(
                    height: 250,
                    child: _buildPieChart(reportsByType),
                  ),
                ),
              ),
            const SizedBox(height: 32),

            // GRÁFICO DE BARRAS (NÍVEL DE RISCO)
            const Text(
              'Relatos por Nível de Risco',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            if (reportsByRisk.isEmpty)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(16.0),
                  child: Text('Nenhum nível de risco registrado.'),
                ),
              )
            else
              Card(
                elevation: 2,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: SizedBox(
                    height: 250,
                    child: _buildBarChart(reportsByRisk),
                  ),
                ),
              ),
            const SizedBox(height: 32),

            // GRÁFICO DE LINHAS (TEMPORAL)
            const Text(
              'Alertas de Pânico (Últimos 7 dias)',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            if (alertsByDate.isEmpty)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(16.0),
                  child: Text('Nenhum alerta registrado nos últimos 7 dias.'),
                ),
              )
            else
              Card(
                elevation: 2,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: SizedBox(
                    height: 250,
                    child: _buildLineChart(alertsByDate),
                  ),
                ),
              ),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }

  Widget _buildStatCard(String title, String value, IconData icon, Color color) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: color, size: 28),
            const SizedBox(height: 8),
            Text(
              value,
              style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            Text(
              title,
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPieChart(List<Map<String, dynamic>> data) {
    final colors = [
      Colors.red,
      Colors.blue,
      Colors.green,
      Colors.orange,
      Colors.purple,
      Colors.teal,
      Colors.pink,
      Colors.indigo,
    ];

    int colorIndex = 0;
    final sections = data.map((item) {
      final tipo = item['tipo_perigo'] as String? ?? 'Desconhecido';
      final count = item['count'] as int? ?? 0;
      final color = colors[colorIndex % colors.length];
      colorIndex++;

      return PieChartSectionData(
        color: color,
        value: count.toDouble(),
        title: count.toString(),
        radius: 50,
        titleStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white),
      );
    }).toList();

    return Row(
      children: [
        Expanded(
          flex: 5,
          child: PieChart(
            PieChartData(
              sectionsSpace: 2,
              centerSpaceRadius: 40,
              sections: sections,
            ),
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          flex: 4,
          child: ListView.builder(
            shrinkWrap: true,
            itemCount: data.length,
            itemBuilder: (context, index) {
              final item = data[index];
              String tipo = item['tipo_perigo'] as String? ?? 'Desconhecido';
              tipo = _formatTypeLabel(tipo);
              final color = colors[index % colors.length];
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 4.0),
                child: Row(
                  children: [
                    Container(
                      width: 12,
                      height: 12,
                      decoration: BoxDecoration(color: color, shape: BoxShape.circle),
                    ),
                    const SizedBox(width: 8),
                    Expanded(child: Text(tipo, style: const TextStyle(fontSize: 12))),
                  ],
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _buildBarChart(List<Map<String, dynamic>> data) {
    final Map<String, Color> riskColors = {
      'baixo': Colors.green,
      'medio': Colors.orange,
      'alto': Colors.red,
    };

    final List<BarChartGroupData> barGroups = [];
    int xIndex = 0;
    
    for (var item in data) {
      final nivel = item['nivel_risco']?.toString().toLowerCase() ?? 'desconhecido';
      final count = item['count'] as int? ?? 0;
      final color = riskColors[nivel] ?? Colors.grey;

      barGroups.add(
        BarChartGroupData(
          x: xIndex,
          barRods: [
            BarChartRodData(
              toY: count.toDouble(),
              color: color,
              width: 30,
              borderRadius: BorderRadius.circular(4),
            ),
          ],
        ),
      );
      xIndex++;
    }

    return BarChart(
      BarChartData(
        alignment: BarChartAlignment.spaceAround,
        barGroups: barGroups,
        titlesData: FlTitlesData(
          show: true,
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              getTitlesWidget: (double value, TitleMeta meta) {
                if (value.toInt() >= 0 && value.toInt() < data.length) {
                  final nivel = data[value.toInt()]['nivel_risco']?.toString() ?? '';
                  return Padding(
                    padding: const EdgeInsets.only(top: 8.0),
                    child: Text(nivel.toUpperCase(), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                  );
                }
                return const Text('');
              },
            ),
          ),
          leftTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: true, reservedSize: 40),
          ),
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
        gridData: const FlGridData(show: false),
        borderData: FlBorderData(show: false),
      ),
    );
  }

  Widget _buildLineChart(List<Map<String, dynamic>> data) {
    final List<FlSpot> spots = [];
    final List<String> dates = [];
    
    for (int i = 0; i < data.length; i++) {
      final dateStr = data[i]['date']?.toString() ?? '';
      String displayDate = dateStr;
      if (dateStr.length >= 10) {
        final parts = dateStr.substring(0, 10).split('-');
        if (parts.length == 3) {
          displayDate = '${parts[2]}/${parts[1]}';
        }
      }
      dates.add(displayDate);
      final count = data[i]['count'] as int? ?? 0;
      spots.add(FlSpot(i.toDouble(), count.toDouble()));
    }

    return LineChart(
      LineChartData(
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            color: AppColors.primary,
            barWidth: 4,
            isStrokeCapRound: true,
            dotData: const FlDotData(show: true),
            belowBarData: BarAreaData(
              show: true,
              color: AppColors.primary.withOpacity(0.2),
            ),
          ),
        ],
        titlesData: FlTitlesData(
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 30,
              interval: 1,
              getTitlesWidget: (value, meta) {
                final index = value.toInt();
                if (index >= 0 && index < dates.length) {
                  return Padding(
                    padding: const EdgeInsets.only(top: 8.0),
                    child: Text(dates[index], style: const TextStyle(fontSize: 10)),
                  );
                }
                return const Text('');
              },
            ),
          ),
          leftTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: true, reservedSize: 40),
          ),
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
        gridData: const FlGridData(show: true, drawVerticalLine: false),
        borderData: FlBorderData(show: false),
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
