import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/user_profile_provider.dart';
import '../providers/app_settings_provider.dart';
import '../services/police_alert_service.dart';
import '../theme/app_colors.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  @override
  void initState() {
    super.initState();
    // Garante que o perfil está carregado ao abrir a tela
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<UserProfileProvider>().loadProfile();
    });
  }

  // Modal para editar os dados básicos (Nome, Telefone e CPF)
  Future<void> _abrirModalEdicaoPerfil(
    UserProfileProvider profileProvider,
  ) async {
    final nomeController = TextEditingController(
      text: profileProvider.nomeCompleto == 'Usuária vigIA' ? '' : profileProvider.nomeCompleto,
    );
    final telefoneController = TextEditingController(text: profileProvider.telefone);
    final cpfController = TextEditingController(text: profileProvider.cpf);

    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return Padding(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(context).viewInsets.bottom,
            left: 24,
            right: 24,
            top: 24,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Editar Informações Pessoais',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: nomeController,
                decoration: const InputDecoration(
                  labelText: 'Nome Completo',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: telefoneController,
                decoration: const InputDecoration(
                  labelText: 'Seu Telefone',
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.phone,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: cpfController,
                decoration: const InputDecoration(
                  labelText: 'CPF (para Banco de Vítimas Reincidentes)',
                  hintText: '123.456.789-00',
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.number,
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.primary,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                  onPressed: () async {
                    try {
                      await profileProvider.updateProfile(
                        nomeCompleto: nomeController.text,
                        telefone: telefoneController.text,
                        cpf: cpfController.text,
                      );
                      if (context.mounted) Navigator.pop(context);
                    } catch (e) {
                      debugPrint('Erro ao salvar perfil: $e');
                    }
                  },
                  child: const Text(
                    'Salvar',
                    style: TextStyle(color: Colors.white),
                  ),
                ),
              ),
              const SizedBox(height: 24),
            ],
          ),
        );
      },
    );
  }

  // Modal para cadastrar um novo contato de emergência na lista
  Future<void> _abrirModalAdicionarContato(
    UserProfileProvider profileProvider,
  ) async {
    final nomeController = TextEditingController();
    final telefoneController = TextEditingController();
    final emailController = TextEditingController();
    final parentescoController = TextEditingController();

    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return Padding(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(context).viewInsets.bottom,
            left: 24,
            right: 24,
            top: 24,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Novo Contato de Emergência',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: nomeController,
                decoration: const InputDecoration(
                  labelText: 'Nome do Contato',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: telefoneController,
                decoration: const InputDecoration(
                  labelText: 'Telefone (para SMS no Android)',
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.phone,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: emailController,
                decoration: const InputDecoration(
                  labelText: 'E-mail (para alerta de emergência)',
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.emailAddress,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: parentescoController,
                decoration: const InputDecoration(
                  labelText: 'Vínculo / Parentesco (Ex: Mãe, Amiga)',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.primary,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                  onPressed: () async {
                    if (nomeController.text.isEmpty ||
                        telefoneController.text.isEmpty) {
                      return;
                    }

                    try {
                      await profileProvider.addEmergencyContact(
                        nome: nomeController.text,
                        telefone: telefoneController.text,
                        email: emailController.text.isEmpty
                            ? null
                            : emailController.text,
                        parentesco: parentescoController.text.isEmpty
                            ? null
                            : parentescoController.text,
                      );
                      if (context.mounted) Navigator.pop(context);
                    } catch (e) {
                      debugPrint('Erro ao adicionar contato: $e');
                    }
                  },
                  child: const Text(
                    'Adicionar',
                    style: TextStyle(color: Colors.white),
                  ),
                ),
              ),
              const SizedBox(height: 24),
            ],
          ),
        );
      },
    );
  }

  Widget _buildContactCard(
    String id,
    String name,
    String phone,
    String? relationship,
  ) {
    String initials = '?';
    if (name.isNotEmpty) {
      List<String> names = name.trim().split(RegExp(r'\s+'));
      if (names.isNotEmpty) {
        initials = names[0][0].toUpperCase();
        if (names.length > 1 && names.last.isNotEmpty) {
          initials += names.last[0].toUpperCase();
        }
      }
    }
    String subtitulo = relationship != null ? '$relationship · $phone' : phone;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.primary.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          CircleAvatar(
            backgroundColor: AppColors.primary,
            radius: 20,
            child: Text(
              initials,
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.bold,
                fontSize: 14,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  name,
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    color: AppColors.primary,
                  ),
                ),
                Text(
                  subtitulo,
                  style: TextStyle(
                    fontSize: 12,
                    color: AppColors.primary.withOpacity(0.8),
                  ),
                ),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(
              Icons.delete_outline,
              color: AppColors.sosRed,
              size: 20,
            ),
            onPressed: () =>
                context.read<UserProfileProvider>().removeEmergencyContact(id),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Consumer2<UserProfileProvider, AppSettingsProvider>(
      builder: (context, profileProvider, settingsProvider, _) {
        String userInitials = 'U';
        if (profileProvider.nomeCompleto.isNotEmpty &&
            profileProvider.nomeCompleto != 'Usuária vigIA') {
          List<String> names = profileProvider.nomeCompleto.trim().split(RegExp(r'\s+'));
          if (names.isNotEmpty) {
            userInitials = names[0][0].toUpperCase();
            if (names.length > 1 && names.last.isNotEmpty) {
              userInitials += names.last[0].toUpperCase();
            }
          }
        }

        return Scaffold(
          appBar: AppBar(
            backgroundColor: AppColors.primary,
            title: const Text('Meu perfil', style: TextStyle(color: Colors.white)),
            actions: [
              IconButton(
                icon: const Icon(Icons.edit, color: Colors.white),
                onPressed: () => _abrirModalEdicaoPerfil(profileProvider),
              ),
            ],
          ),
          body: profileProvider.isLoading
              ? const Center(child: CircularProgressIndicator())
              : ListView(
                  padding: const EdgeInsets.all(24),
                  children: [
                    CircleAvatar(
                      radius: 40,
                      backgroundColor: AppColors.primary.withOpacity(0.1),
                      child: Text(
                        userInitials,
                        style: const TextStyle(
                          fontSize: 28,
                          color: AppColors.primary,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      profileProvider.nomeCompleto,
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Text(
                      profileProvider.email,
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.grey),
                    ),
                    const SizedBox(height: 4),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          profileProvider.cpf.isNotEmpty
                              ? 'CPF: ${profileProvider.cpf}'
                              : 'CPF: Não cadastrado',
                          style: const TextStyle(fontSize: 13, color: Colors.black87),
                        ),
                        IconButton(
                          icon: const Icon(Icons.edit, size: 16, color: AppColors.primary),
                          onPressed: () => _abrirModalEdicaoPerfil(profileProvider),
                          tooltip: 'Editar CPF',
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),

                    const Text(
                      'BANCO DE VÍTIMAS REINCIDENTES & POLÍCIA',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: Colors.grey,
                      ),
                    ),
                    const SizedBox(height: 8),
                    FutureBuilder<bool>(
                      future: PoliceAlertService.instance.isCpfCadastradoNoBanco(profileProvider.cpf),
                      builder: (context, snapshot) {
                        final isCadastrada = snapshot.data ?? false;
                        return Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: isCadastrada ? const Color(0xFFEFF6FF) : const Color(0xFFFFFBEB),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: isCadastrada ? const Color(0xFF93C5FD) : const Color(0xFFFDE68A),
                            ),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Icon(
                                    isCadastrada ? Icons.shield : Icons.warning_amber_rounded,
                                    color: isCadastrada ? const Color(0xFF1D4ED8) : const Color(0xFFB45309),
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      isCadastrada
                                          ? 'Cadastrada no Banco de Vítimas Reincidentes'
                                          : 'Não cadastrada no Banco de Vítimas Reincidentes',
                                      style: TextStyle(
                                        fontWeight: FontWeight.bold,
                                        color: isCadastrada ? const Color(0xFF1E3A8A) : const Color(0xFF92400E),
                                        fontSize: 14,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 8),
                              Text(
                                isCadastrada
                                    ? '🚨 Ao acionar o botão de emergência, a Polícia Militar (190) receberá um alerta prioritário automático com a sua localização, além de notificar seus contatos de emergência.'
                                    : '⚠️ Ao acionar o botão de emergência, apenas seus contatos de emergência cadastrados serão notificados.',
                                style: const TextStyle(fontSize: 12, color: Colors.black54),
                              ),
                              const SizedBox(height: 12),
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  const Text(
                                    'Simular no Supabase (recurring_victims):',
                                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                                  ),
                                  Switch(
                                    value: isCadastrada,
                                    activeThumbColor: AppColors.primary,
                                    onChanged: (val) async {
                                      if (profileProvider.cpf.isEmpty) {
                                        ScaffoldMessenger.of(context).showSnackBar(
                                          const SnackBar(
                                            content: Text('Cadastre um CPF primeiro para simular o banco de vítimas.'),
                                          ),
                                        );
                                        return;
                                      }
                                      await PoliceAlertService.instance.alternarCpfNoBanco(
                                        profileProvider.cpf,
                                        profileProvider.nomeCompleto,
                                      );
                                      setState(() {});
                                    },
                                  ),
                                ],
                              ),
                            ],
                          ),
                        );
                      },
                    ),
                    const SizedBox(height: 24),

                    const Text(
                      'CONFIGURAÇÕES',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: Colors.grey,
                      ),
                    ),
                    const SizedBox(height: 8),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      activeThumbColor: AppColors.primary,
                      title: const Text(
                        'Compartilhar localização',
                        style: TextStyle(fontSize: 15),
                      ),
                      value: settingsProvider.locationSharingEnabled,
                      onChanged: (_) => settingsProvider.toggleLocationSharing(),
                    ),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      activeThumbColor: AppColors.primary,
                      title: const Text(
                        'Alertas por push',
                        style: TextStyle(fontSize: 15),
                      ),
                      value: settingsProvider.pushAlertsEnabled,
                      onChanged: (_) => settingsProvider.togglePushAlerts(),
                    ),
                    const ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(
                        'Identidade verificada',
                        style: TextStyle(fontSize: 15),
                      ),
                      trailing: Chip(
                        label: Text(
                          'Verificada',
                          style: TextStyle(color: Color(0xFF27500A), fontSize: 11),
                        ),
                        backgroundColor: Color(0xFFEAF3DE),
                        side: BorderSide.none,
                      ),
                    ),

                    const SizedBox(height: 24),
                    const Text(
                      'CONTATOS DE EMERGÊNCIA',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: Colors.grey,
                      ),
                    ),
                    const SizedBox(height: 12),

                    // Renderiza a lista dinâmica mapeada direto do provider
                    profileProvider.contatosEmergencia.isEmpty
                        ? const Padding(
                            padding: EdgeInsets.symmetric(vertical: 8.0),
                            child: Text(
                              'Nenhum contato de emergência cadastrado.',
                              style: TextStyle(color: Colors.grey, fontSize: 14),
                            ),
                          )
                        : Column(
                            children: profileProvider.contatosEmergencia.map((contato) {
                              return _buildContactCard(
                                contato['id'].toString(),
                                contato['nome'] ?? 'Sem nome',
                                contato['telefone'] ?? '',
                                contato['parentesco'],
                              );
                            }).toList(),
                          ),

                    const SizedBox(height: 16),
                    OutlinedButton(
                      onPressed: () => _abrirModalAdicionarContato(profileProvider),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppColors.primary,
                        side: const BorderSide(color: AppColors.primary),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        padding: const EdgeInsets.symmetric(vertical: 14),
                      ),
                      child: const Text('+ Adicionar contato'),
                    ),
                  ],
                ),
        );
      },
    );
  }
}
