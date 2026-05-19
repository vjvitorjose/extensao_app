import 'package:flutter/material.dart';
import '../theme/app_colors.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  bool locShared = true;
  bool pushAlerts = true;

  Widget _buildContactCard(String initials, String name, String relationPhone) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: AppColors.riskAssedioBg, borderRadius: BorderRadius.circular(12)),
      child: Row(
        children: [
          CircleAvatar(
            backgroundColor: AppColors.primary,
            radius: 20,
            child: Text(initials, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
          ),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(name, style: const TextStyle(fontWeight: FontWeight.bold, color: AppColors.riskAssedioText)),
              Text(relationPhone, style: const TextStyle(fontSize: 12, color: Color(0xFF993556))),
            ],
          )
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: AppColors.primary,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: const [
            Text('Meu perfil', style: TextStyle(fontSize: 18, color: Colors.white)),
            Text('Configurações e contatos de emergência', style: TextStyle(fontSize: 12, color: Colors.white70)),
          ],
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          const CircleAvatar(
            radius: 40,
            backgroundColor: AppColors.riskAssedioBg,
            child: Text('MA', style: TextStyle(fontSize: 28, color: AppColors.riskAssedioText, fontWeight: FontWeight.bold)),
          ),
          const SizedBox(height: 12),
          const Text('Maria Aparecida', textAlign: TextAlign.center, style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
          const Text('maria@email.com', textAlign: TextAlign.center, style: TextStyle(color: Colors.grey)),
          const SizedBox(height: 32),
          
          const Text('CONFIGURAÇÕES', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.grey)),
          const SizedBox(height: 8),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            activeThumbColor: AppColors.primary,
            title: const Text('Compartilhar localização', style: TextStyle(fontSize: 15)),
            value: locShared,
            onChanged: (val) => setState(() => locShared = val),
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            activeThumbColor: AppColors.primary,
            title: const Text('Alertas por push', style: TextStyle(fontSize: 15)),
            value: pushAlerts,
            onChanged: (val) => setState(() => pushAlerts = val),
          ),
          const ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text('Identidade verificada', style: TextStyle(fontSize: 15)),
            trailing: Chip(
              label: Text('Verificada', style: TextStyle(color: Color(0xFF27500A), fontSize: 11)),
              backgroundColor: Color(0xFFEAF3DE),
              side: BorderSide.none,
            ),
          ),
          
          const SizedBox(height: 24),
          const Text('CONTATOS DE EMERGÊNCIA', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.grey)),
          const SizedBox(height: 12),
          _buildContactCard('JA', 'Joana Aparecida', 'Mãe · (32) 99999-0001'),
          _buildContactCard('PS', 'Paula Santos', 'Amiga · (32) 99999-0002'),
          
          const SizedBox(height: 12),
          OutlinedButton(
            onPressed: () {},
            style: OutlinedButton.styleFrom(
              foregroundColor: AppColors.primary,
              side: const BorderSide(color: AppColors.primary),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              padding: const EdgeInsets.symmetric(vertical: 14),
            ),
            child: const Text('+ Adicionar contato'),
          ),
        ],
      ),
    );
  }
}