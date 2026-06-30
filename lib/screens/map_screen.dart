import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:geolocator/geolocator.dart';
import 'package:flutter/foundation.dart'
    show kIsWeb, defaultTargetPlatform, TargetPlatform;
import 'package:geocoding/geocoding.dart';
import 'package:http/http.dart' as http;
import 'package:another_telephony/telephony.dart';
import 'dart:convert';
import '../theme/app_colors.dart';
import 'sos_screen.dart';

bool _modalAberto = false;

class MapScreen extends StatefulWidget {
  const MapScreen({super.key});

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  GoogleMapController? mapController;
  final supabase = Supabase.instance.client;

  LatLng _minhaLocalizacao = const LatLng(-21.1355, -44.2616);
  LatLng? _localSelecionado;
  bool _usarLocalMarcadoParaAlerta = false;
  bool _carregandoLocalizacao = true;

  @override
  void initState() {
    super.initState();
    _inicializarMapa();
  }

  Future<void> _inicializarMapa() async {
    await _obterLocalizacaoAtual();
  }

  Future<void> _obterLocalizacaoAtual() async {
    bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) return;

    LocationPermission permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) return;
    }

    if (permission == LocationPermission.deniedForever) return;

    Position position = await Geolocator.getCurrentPosition();
    setState(() {
      _minhaLocalizacao = LatLng(position.latitude, position.longitude);
      _carregandoLocalizacao = false;
    });

    mapController?.animateCamera(
      CameraUpdate.newLatLngZoom(_minhaLocalizacao, 16.0),
    );
  }

  Future<void> _salvarAlerta(
    String categoriaVisual,
    String descricao,
    bool isAnonimo,
    bool usarLocalMarcado,
  ) async {
    final user = supabase.auth.currentUser;

    String tipoBanco = 'area_deserta';
    if (categoriaVisual == 'Assédio') tipoBanco = 'assedio';
    if (categoriaVisual == 'Iluminação ruim') tipoBanco = 'iluminacao_ruim';
    if (categoriaVisual == 'Perseguição') tipoBanco = 'perseguicao';
    if (categoriaVisual == 'Local suspeito') tipoBanco = 'area_deserta';

    try {
      final double lat;
      final double lng;

      if (usarLocalMarcado && _localSelecionado != null) {
        lat = _localSelecionado!.latitude;
        lng = _localSelecionado!.longitude;
      } else {
        final Position posicao = await Geolocator.getCurrentPosition();
        lat = posicao.latitude;
        lng = posicao.longitude;
      }

      String? enderecoDescoberto;
      try {
        if (kIsWeb) {
          final url = Uri.parse(
            'https://nominatim.openstreetmap.org/reverse?format=json&lat=$lat&lon=$lng&zoom=18&addressdetails=1',
          );
          final response = await http.get(
            url,
            headers: {'User-Agent': 'SafeHerApp/1.0'},
          );

          if (response.statusCode == 200) {
            final data = json.decode(response.body);
            if (data != null && data['address'] != null) {
              final address = data['address'];
              String rua = address['road'] ?? address['pedestrian'] ?? '';
              String bairro =
                  address['suburb'] ?? address['neighbourhood'] ?? '';
              enderecoDescoberto = (rua.isNotEmpty && bairro.isNotEmpty)
                  ? '$rua, $bairro'
                  : rua;
            }
          }
        } else {
          final List<Placemark> placemarks = await placemarkFromCoordinates(
            lat,
            lng,
          );
          if (placemarks.isNotEmpty) {
            final Placemark place = placemarks[0];
            String rua = place.street ?? '';
            String bairro = place.subLocality ?? '';
            enderecoDescoberto = (rua.isNotEmpty && bairro.isNotEmpty)
                ? '$rua, $bairro'
                : rua;
          }
        }
      } catch (e) {
        debugPrint('Não foi possível obter o endereço: $e');
      }

      final idParaSalvar = isAnonimo ? null : user?.id;

      await supabase.from('danger_reports').insert({
        'usuario_id': idParaSalvar,
        'tipo_perigo': tipoBanco,
        'descricao': descricao.isEmpty ? null : descricao,
        'latitude': lat,
        'longitude': lng,
        'endereco': enderecoDescoberto,
      });

      setState(() {
        _localSelecionado = null;
        _usarLocalMarcadoParaAlerta = false;
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Alerta registrado com sucesso!')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Erro ao salvar: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  bool _enviandoPanico = false;

  // Aciona o botão de pânico: avisa os contatos de emergência por e-mail
  // (todas as plataformas, via Edge Function) e por SMS (somente Android).
  Future<void> _acionarPanico() async {
    if (_enviandoPanico) return;

    // Confirmação rápida para evitar disparos acidentais.
    final confirmar = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Acionar emergência?'),
        content: const Text(
          'Seus contatos de emergência serão avisados imediatamente com a sua '
          'localização atual.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancelar'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.sosRed),
            onPressed: () => Navigator.pop(context, true),
            child: const Text(
              'Acionar agora',
              style: TextStyle(color: Colors.white),
            ),
          ),
        ],
      ),
    );

    if (confirmar != true) return;

    setState(() => _enviandoPanico = true);

    try {
      final user = supabase.auth.currentUser;

      // 1. Tenta obter a localização atual (não bloqueia o alerta se falhar).
      double? lat;
      double? lng;
      try {
        final posicao = await Geolocator.getCurrentPosition();
        lat = posicao.latitude;
        lng = posicao.longitude;
      } catch (e) {
        debugPrint('Não foi possível obter localização no pânico: $e');
      }

      // 2. Busca o nome da usuária e os contatos (telefones para o SMS).
      String nomeUsuaria = 'Uma usuária do SafeHer';
      List<Map<String, dynamic>> contatos = [];
      if (user != null) {
        final perfil = await supabase
            .from('profiles')
            .select('nome_completo')
            .eq('id', user.id)
            .maybeSingle();
        if (perfil != null && perfil['nome_completo'] != null) {
          nomeUsuaria = perfil['nome_completo'];
        }

        final dadosContatos = await supabase
            .from('emergency_contacts')
            .select()
            .eq('profile_id', user.id);
        contatos = List<Map<String, dynamic>>.from(dadosContatos);
      }

      // 3. Dispara os e-mails pelo servidor (Edge Function).
      await supabase.functions.invoke(
        'panic-alert',
        body: {'latitude': lat, 'longitude': lng},
      );

      // 4. No Android, também envia SMS pelo chip do aparelho.
      if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
        await _enviarSmsAndroid(nomeUsuaria, contatos, lat, lng);
      }

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('🚨 Alerta enviado aos seus contatos de emergência!'),
            backgroundColor: AppColors.sosRed,
          ),
        );
      }
    } catch (e) {
      debugPrint('Erro ao acionar pânico: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Erro ao enviar alerta: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _enviandoPanico = false);
    }
  }

  Future<void> _enviarSmsAndroid(
    String nomeUsuaria,
    List<Map<String, dynamic>> contatos,
    double? lat,
    double? lng,
  ) async {
    final telephony = Telephony.instance;
    final permitido = await telephony.requestSmsPermissions ?? false;
    if (!permitido) return;

    final linkMapa = (lat != null && lng != null)
        ? 'https://www.google.com/maps?q=$lat,$lng'
        : 'localização indisponível';
    final mensagem =
        '🚨 $nomeUsuaria acionou um alerta de emergência (SafeHer). '
        'Localização: $linkMapa';

    for (final contato in contatos) {
      final telefone = (contato['telefone'] ?? '').toString().trim();
      if (telefone.isEmpty) continue;
      try {
        await telephony.sendSms(to: telefone, message: mensagem);
      } catch (e) {
        debugPrint('Falha ao enviar SMS para $telefone: $e');
      }
    }
  }

  void _abrirModalRisco(BuildContext context) {
    setState(() {
      _modalAberto = true;
    });

    String? categoriaSelecionada;
    final descricaoController = TextEditingController();
    bool relatoAnonimo = false;

    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      isScrollControlled: true,
      builder: (context) {
        return StatefulBuilder(
          builder: (BuildContext context, StateSetter setModalState) {
            bool usarLocalMarcadoNoModal =
                _localSelecionado != null && _usarLocalMarcadoParaAlerta;

            final String textoOrigemLocal = usarLocalMarcadoNoModal
                ? '📍 O alerta será registrado no ponto marcado no mapa'
                : '📡 O alerta será registrado com sua localização atual (GPS)';

            final String textoBotao = usarLocalMarcadoNoModal
                ? 'Registrar neste local'
                : 'Registrar com meu GPS';

            return Padding(
              padding: EdgeInsets.only(
                bottom: MediaQuery.of(context).viewInsets.bottom,
                left: 20,
                right: 20,
                top: 20,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Center(
                    child: Container(
                      width: 36,
                      height: 4,
                      margin: const EdgeInsets.only(bottom: 16),
                      decoration: BoxDecoration(
                        color: Colors.grey[300],
                        borderRadius: BorderRadius.circular(2),
                      ),
                    ),
                  ),
                  const Text(
                    'Marcar local de risco',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    textoOrigemLocal,
                    style: TextStyle(
                      fontSize: 12,
                      color: _localSelecionado != null
                          ? AppColors.primary
                          : Colors.grey,
                    ),
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Origem do alerta',
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    children: [
                      ChoiceChip(
                        label: const Text('GPS atual'),
                        selected: !usarLocalMarcadoNoModal,
                        onSelected: (selected) {
                          if (selected) {
                            setModalState(() {
                              usarLocalMarcadoNoModal = false;
                            });
                            setState(() {
                              _usarLocalMarcadoParaAlerta = false;
                            });
                          }
                        },
                      ),
                      ChoiceChip(
                        label: const Text('Ponto marcado'),
                        selected: usarLocalMarcadoNoModal,
                        selectedColor: AppColors.primary.withAlpha(30),
                        onSelected: _localSelecionado == null
                            ? null
                            : (selected) {
                                if (selected) {
                                  setModalState(() {
                                    usarLocalMarcadoNoModal = true;
                                  });
                                  setState(() {
                                    _usarLocalMarcadoParaAlerta = true;
                                  });
                                }
                              },
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      _buildEscolha(
                        setModalState,
                        'Assédio',
                        categoriaSelecionada,
                        (val) => categoriaSelecionada = val,
                        AppColors.riskAssedioBg,
                        AppColors.riskAssedioText,
                      ),
                      _buildEscolha(
                        setModalState,
                        'Iluminação ruim',
                        categoriaSelecionada,
                        (val) => categoriaSelecionada = val,
                        AppColors.riskIluminacaoBg,
                        AppColors.riskIluminacaoText,
                      ),
                      _buildEscolha(
                        setModalState,
                        'Perseguição',
                        categoriaSelecionada,
                        (val) => categoriaSelecionada = val,
                        AppColors.riskPerseguicaoBg,
                        AppColors.riskPerseguicaoText,
                      ),
                      _buildEscolha(
                        setModalState,
                        'Local suspeito',
                        categoriaSelecionada,
                        (val) => categoriaSelecionada = val,
                        AppColors.riskSuspeitoBg,
                        AppColors.riskSuspeitoText,
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: descricaoController,
                    decoration: InputDecoration(
                      hintText: 'Descreva o ocorrido (opcional)...',
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                      contentPadding: const EdgeInsets.all(12),
                    ),
                    maxLines: 3,
                  ),
                  const SizedBox(height: 16),
                  SwitchListTile(
                    title: const Text(
                      'Relatar anonimamente',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    subtitle: const Text(
                      'Seu nome e perfil não serão vinculados a este alerta.',
                      style: TextStyle(fontSize: 12),
                    ),
                    value: relatoAnonimo,
                    activeColor: AppColors.primary,
                    contentPadding: EdgeInsets.zero,
                    onChanged: (bool valor) {
                      setModalState(() {
                        relatoAnonimo = valor;
                      });
                    },
                  ),
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: categoriaSelecionada != null
                            ? AppColors.primary
                            : Colors.grey,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                      onPressed: categoriaSelecionada == null
                          ? null
                          : () {
                              Navigator.pop(context);
                              _salvarAlerta(
                                categoriaSelecionada!,
                                descricaoController.text,
                                relatoAnonimo,
                                usarLocalMarcadoNoModal,
                              );
                            },
                      child: Text(
                        textoBotao,
                        style: const TextStyle(color: Colors.white),
                      ),
                    ),
                  ),
                  const SizedBox(height: 20),
                ],
              ),
            );
          },
        );
      },
    ).then((_) {
      setState(() {
        _modalAberto = false;
      });
    });
  }

  Widget _buildEscolha(
    StateSetter setModalState,
    String label,
    String? atual,
    Function(String) onSelect,
    Color bg,
    Color text,
  ) {
    final selecionado = label == atual;
    return GestureDetector(
      onTap: () => setModalState(() => onSelect(label)),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: selecionado ? bg : Colors.grey.shade100,
          border: Border.all(color: selecionado ? text : Colors.transparent),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: selecionado ? text : Colors.black54,
            fontSize: 12,
            fontWeight: FontWeight.w500,
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: AppColors.primary,
        title: const Text('SafeHer', style: TextStyle(color: Colors.white)),
      ),
      body: Stack(
        children: [
          GoogleMap(
            onMapCreated: (controller) => mapController = controller,
            initialCameraPosition: CameraPosition(
              target: _minhaLocalizacao,
              zoom: 15.0,
            ),
            markers: _localSelecionado != null
                ? {
                    Marker(
                      markerId: const MarkerId('pino_manual'),
                      position: _localSelecionado!,
                      icon: BitmapDescriptor.defaultMarkerWithHue(
                        BitmapDescriptor.hueBlue,
                      ),
                      infoWindow: const InfoWindow(
                        title: 'Local selecionado',
                        snippet: 'Relatar risco aqui',
                      ),
                    ),
                  }
                : {},
            myLocationEnabled: true,
            myLocationButtonEnabled: true,
            zoomControlsEnabled: false,
            onTap: (LatLng position) {
              if (_modalAberto) return;
              setState(() {
                _localSelecionado = position;
                _usarLocalMarcadoParaAlerta = true;
              });
            },
          ),
          if (_carregandoLocalizacao)
            const Center(child: CircularProgressIndicator()),
          if (_localSelecionado != null)
            Positioned(
              bottom: 132,
              right: 24,
              child: FloatingActionButton.small(
                heroTag: 'clear_btn',
                backgroundColor: Colors.white,
                onPressed: () => setState(() {
                  _localSelecionado = null;
                  _usarLocalMarcadoParaAlerta = false;
                }),
                child: const Icon(Icons.close, color: Colors.black54),
              ),
            ),
          Positioned(
            bottom: 24,
            left: 16,
            child: FloatingActionButton.extended(
              heroTag: 'sos_btn',
              backgroundColor: AppColors.sosRed,
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const SosScreen()),
                );
              },
              label: const Text('SOS', style: TextStyle(color: Colors.white)),
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

          // Botão de pânico (SOS) — avisa os contatos de emergência na hora.
          Positioned(
            bottom: 24,
            left: 16,
            child: FloatingActionButton.extended(
              heroTag: 'panic_btn',
              backgroundColor: AppColors.sosRed,
              onPressed: _enviandoPanico ? null : _acionarPanico,
              icon: _enviandoPanico
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Icon(Icons.sos, color: Colors.white),
              label: Text(
                _enviandoPanico ? 'Enviando...' : 'SOS',
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
