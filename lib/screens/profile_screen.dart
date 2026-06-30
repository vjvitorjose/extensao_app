import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../theme/app_colors.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final supabase = Supabase.instance.client;

  bool locShared = true;
  bool pushAlerts = true;
  bool _carregando = true;

  // Dados do Perfil
  String _nomeCompleto = 'Carregando...';
  String _email = '';
  String _telefone = '';

  // Lista dinâmica para múltiplos contatos de emergência
  List<Map<String, dynamic>> _contatosEmergencia = [];

  @override
  void initState() {
    super.initState();
    _carregarDadosIniciais();
  }

  // Carrega o perfil e a lista de contatos do Supabase
  Future<void> _carregarDadosIniciais() async {
    try {
      final user = supabase.auth.currentUser;
      if (user == null) return;

      setState(() {
        _email = user.email ?? 'Sem e-mail';
      });

      // 1. Busca os dados do perfil básico
      final perfilDados = await supabase
          .from('profiles')
          .select()
          .eq('id', user.id)
          .maybeSingle();

      if (perfilDados != null) {
        _nomeCompleto = perfilDados['nome_completo'] ?? 'Usuária SafeHer';
        _telefone = perfilDados['telefone'] ?? '';
      } else {
        _nomeCompleto = 'Usuária SafeHer';
      }

      // 2. Busca a lista de múltiplos contatos de emergência
      final contatosDados = await supabase
          .from('emergency_contacts')
          .select()
          .eq('profile_id', user.id)
          .order('criado_em', ascending: true);

      setState(() {
        _contatosEmergencia = List<Map<String, dynamic>>.from(contatosDados);
      });
    } catch (e) {
      debugPrint('Erro ao carregar dados do perfil: $e');
    } finally {
      setState(() {
        _carregando = false;
      });
    }
  }

  // Modal para editar os dados básicos (Nome e Telefone)
  Future<void> _abrirModalEdicaoPerfil() async {
    final nomeController = TextEditingController(
      text: _nomeCompleto == 'Usuária SafeHer' ? '' : _nomeCompleto,
    );
    final telefoneController = TextEditingController(text: _telefone);

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
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.primary,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                  onPressed: () async {
                    final user = supabase.auth.currentUser;
                    if (user == null) return;

                    try {
                      await supabase.from('profiles').upsert({
                        'id': user.id,
                        'nome_completo': nomeController.text,
                        'telefone': telefoneController.text,
                        'atualizado_em': DateTime.now().toIso8601String(),
                      });
                      _carregarDadosIniciais();
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
  Future<void> _abrirModalAdicionarContato() async {
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
                    final user = supabase.auth.currentUser;
                    if (user == null) return;

                    if (nomeController.text.isEmpty ||
                        telefoneController.text.isEmpty) {
                      return;
                    }

                    try {
                      await supabase.from('emergency_contacts').insert({
                        'profile_id': user.id,
                        'nome': nomeController.text,
                        'telefone': telefoneController.text,
                        'email': emailController.text.isEmpty
                            ? null
                            : emailController.text.trim(),
                        'parentesco': parentescoController.text.isEmpty
                            ? null
                            : parentescoController.text,
                      });
                      _carregarDadosIniciais();
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

  // Remove um contato específico da tabela
  Future<void> _deletarContato(String contatoId) async {
    try {
      await supabase.from('emergency_contacts').delete().eq('id', contatoId);
      _carregarDadosIniciais();
    } catch (e) {
      debugPrint('Erro ao deletar contato: $e');
    }
  }

  Widget _buildContactCard(
    String id,
    String name,
    String phone,
    String? relationship,
  ) {
    String initials = name.isNotEmpty ? name.toUpperCase() : '?';
    String subtitulo = relationship != null ? '$relationship · $phone' : phone;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.riskAssedioBg,
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
                    color: AppColors.riskAssedioText,
                  ),
                ),
                Text(
                  subtitulo,
                  style: const TextStyle(
                    fontSize: 12,
                    color: Color(0xFF993556),
                  ),
                ),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(
              Icons.delete_outline,
              color: Color(0xFF993556),
              size: 20,
            ),
            onPressed: () => _deletarContato(id),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    String userInitials = 'U';
    if (_nomeCompleto.isNotEmpty && _nomeCompleto != 'Usuária SafeHer') {
      List<String> names = _nomeCompleto.split(' ');
      userInitials = names[0].toUpperCase();
      if (names.length > 1 && names.last.isNotEmpty) {
        userInitials = names[0].toUpperCase();
      }
    }

    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: AppColors.primary,
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Meu perfil',
              style: TextStyle(fontSize: 18, color: Colors.white),
            ),
            Text(
              'Configurações e contatos de emergência',
              style: TextStyle(fontSize: 12, color: Colors.white70),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.edit, color: Colors.white),
            onPressed: _abrirModalEdicaoPerfil,
          ),
        ],
      ),
      body: _carregando
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(24),
              children: [
                CircleAvatar(
                  radius: 40,
                  backgroundColor: AppColors.riskAssedioBg,
                  child: Text(
                    userInitials,
                    style: const TextStyle(
                      fontSize: 28,
                      color: AppColors.riskAssedioText,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  _nomeCompleto,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  _email,
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.grey),
                ),
                const SizedBox(height: 32),

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
                  value: locShared,
                  onChanged: (val) => setState(() => locShared = val),
                ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  activeThumbColor: AppColors.primary,
                  title: const Text(
                    'Alertas por push',
                    style: TextStyle(fontSize: 15),
                  ),
                  value: pushAlerts,
                  onChanged: (val) => setState(() => pushAlerts = val),
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

                // Renderiza a lista dinâmica mapeada direto do banco
                _contatosEmergencia.isEmpty
                    ? const Padding(
                        padding: EdgeInsets.symmetric(vertical: 8.0),
                        child: Text(
                          'Nenhum contato de emergência cadastrado.',
                          style: TextStyle(color: Colors.grey, fontSize: 14),
                        ),
                      )
                    : Column(
                        children: _contatosEmergencia.map((contato) {
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
                  onPressed: _abrirModalAdicionarContato,
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
  }
}
