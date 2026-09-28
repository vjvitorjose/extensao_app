import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../screens/admin_map_screen.dart';
import '../screens/dashboard_screen.dart';

class AdminDrawer extends StatelessWidget {
  const AdminDrawer({super.key});

  @override
  Widget build(BuildContext context) {
    final currentRoute = ModalRoute.of(context)?.settings.name;

    return Drawer(
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          const DrawerHeader(
            decoration: BoxDecoration(
              color: AppColors.primary,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                Icon(Icons.admin_panel_settings, color: Colors.white, size: 48),
                SizedBox(height: 12),
                Text(
                  'Painel Administrativo',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
          ),
          ListTile(
            leading: const Icon(Icons.dashboard),
            title: const Text('Dashboard'),
            selected: currentRoute == '/admin/dashboard',
            selectedColor: AppColors.primary,
            onTap: () {
              Navigator.pop(context); // close drawer
              if (currentRoute != '/admin/dashboard') {
                Navigator.pushReplacement(
                  context,
                  MaterialPageRoute(builder: (_) => const DashboardScreen(), settings: const RouteSettings(name: '/admin/dashboard')),
                );
              }
            },
          ),
          ListTile(
            leading: const Icon(Icons.map),
            title: const Text('Mapa de Alertas'),
            selected: currentRoute == '/admin/map' || currentRoute == null, // default
            selectedColor: AppColors.primary,
            onTap: () {
              Navigator.pop(context); // close drawer
              if (currentRoute != '/admin/map' && currentRoute != null) {
                Navigator.pushReplacement(
                  context,
                  MaterialPageRoute(builder: (_) => const AdminMapScreen(), settings: const RouteSettings(name: '/admin/map')),
                );
              }
            },
          ),
          const Divider(),
          ListTile(
            leading: const Icon(Icons.exit_to_app),
            title: const Text('Voltar para o App'),
            onTap: () {
              Navigator.pop(context); // close drawer
              Navigator.pop(context); // exit admin area (voltar pra tela anterior)
            },
          ),
        ],
      ),
    );
  }
}
