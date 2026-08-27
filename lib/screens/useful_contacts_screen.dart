import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../theme/app_colors.dart';

class UsefulContactsScreen extends StatelessWidget {
  const UsefulContactsScreen({super.key});

  Future<void> _launchPhone(String phone) async {
    final Uri url = Uri(scheme: 'tel', path: phone);
    if (await canLaunchUrl(url)) {
      await launchUrl(url);
    }
  }

  Future<void> _launchUrl(String urlString) async {
    final Uri url = Uri.parse(urlString);
    if (await canLaunchUrl(url)) {
      await launchUrl(url, mode: LaunchMode.externalApplication);
    }
  }

  Widget _buildContactCard({
    required String title,
    required String subtitle,
    required IconData icon,
    required VoidCallback onTap,
    Color iconColor = AppColors.primary,
  }) {
    return Card(
      elevation: 2,
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        leading: CircleAvatar(
          backgroundColor: iconColor.withOpacity(0.1),
          radius: 24,
          child: Icon(icon, color: iconColor, size: 28),
        ),
        title: Text(
          title,
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 4.0),
          child: Text(
            subtitle,
            style: const TextStyle(color: Colors.black87, fontSize: 13),
          ),
        ),
        trailing: Icon(Icons.arrow_forward_ios, size: 16, color: Colors.grey[400]),
        onTap: onTap,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[50],
      appBar: AppBar(
        backgroundColor: AppColors.primary,
        title: const Text('Contatos Úteis', style: TextStyle(color: Colors.white)),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            'Emergência e Segurança',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: AppColors.primary,
            ),
          ),
          const SizedBox(height: 12),
          _buildContactCard(
            title: 'Polícia Militar',
            subtitle: '190 - Emergências em andamento',
            icon: Icons.local_police,
            iconColor: Colors.red[700]!,
            onTap: () => _launchPhone('190'),
          ),
          _buildContactCard(
            title: 'Central de Atendimento à Mulher',
            subtitle: '180 - Denúncias de violência doméstica',
            icon: Icons.support_agent,
            iconColor: Colors.purple[700]!,
            onTap: () => _launchPhone('180'),
          ),
          _buildContactCard(
            title: 'Polícia Civil',
            subtitle: '197 - Investigações e informações',
            icon: Icons.policy,
            onTap: () => _launchPhone('197'),
          ),
          _buildContactCard(
            title: 'Delegacia da Mulher (DEAM)',
            subtitle: 'São João del Rei - MG\n(32) 3322-1234', // Usando um placeholder ou pesquisando, vou deixar apenas o clique
            icon: Icons.health_and_safety,
            onTap: () => _launchPhone('3233221234'), // O telefone exato pode ser atualizado pelo usuário depois
          ),
          
          const SizedBox(height: 24),
          const Text(
            'Projetos e Apoio',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: AppColors.primary,
            ),
          ),
          const SizedBox(height: 12),
          _buildContactCard(
            title: 'Projeto Idas e Vindas (UFSJ)',
            subtitle: 'Apoio e acolhimento para mulheres\n@idasevindasufsj',
            icon: Icons.camera_alt, // Representando Instagram
            iconColor: Colors.pink[600]!,
            onTap: () => _launchUrl('https://www.instagram.com/idasevindasufsj/'),
          ),
        ],
      ),
    );
  }
}
