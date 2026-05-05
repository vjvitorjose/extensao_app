import 'package:flutter/material.dart';
import '../theme/app_colors.dart';

class AlertsScreen extends StatelessWidget {
  const AlertsScreen({super.key});

  Widget _buildAlertCard(String category, Color catBg, Color catColor, String time, String address, String desc, String distance) {
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
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(color: catBg, borderRadius: BorderRadius.circular(20)),
                child: Text(category, style: TextStyle(color: catColor, fontSize: 11, fontWeight: FontWeight.bold)),
              ),
              Text(time, style: const TextStyle(fontSize: 11, color: Colors.grey)),
            ],
          ),
          const SizedBox(height: 12),
          Text(address, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold)),
          const SizedBox(height: 4),
          Text(desc, style: const TextStyle(fontSize: 13, color: Colors.black54)),
          const SizedBox(height: 8),
          Text(distance, style: const TextStyle(fontSize: 12, color: AppColors.primary, fontWeight: FontWeight.bold)),
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
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: const [
            Text('Alertas próximos', style: TextStyle(fontSize: 18, color: Colors.white)),
            Text('Raio de 2 km da sua localização', style: TextStyle(fontSize: 12, color: Colors.white70)),
          ],
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _buildAlertCard('Perseguição', AppColors.riskPerseguicaoBg, AppColors.riskPerseguicaoText, 'há 12 min', 'R. Padre José Maria Xavier, 220', 'Homem seguindo a pé desde a praça', '320 m de você'),
          _buildAlertCard('Assédio', AppColors.riskAssedioBg, AppColors.riskAssedioText, 'há 45 min', 'Praça Dr. Antônio Mourão Guimarães', 'Homem abordando mulheres no local', '580 m de você'),
          _buildAlertCard('Iluminação ruim', AppColors.riskIluminacaoBg, AppColors.riskIluminacaoText, 'há 2 h', 'R. Marechal Deodoro, trecho escuro', 'Postes apagados no trecho entre os nº 80–120', '1,2 km de você'),
          _buildAlertCard('Local suspeito', AppColors.riskSuspeitoBg, AppColors.riskSuspeitoText, 'há 3 h', 'Beco da R. Artur Bernardes', 'Beco sem saída, pouca visibilidade', '1,8 km de você'),
        ],
      ),
    );
  }
}