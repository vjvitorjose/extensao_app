import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:geolocator/geolocator.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:geocoding/geocoding.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../theme/app_colors.dart';

bool _modalAberto = false;

class MapScreen extends StatefulWidget {
  const MapScreen({super.key});

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  GoogleMapController? mapController;
  final supabase = Supabase.instance.client;

  LatLng _minhaLocalizacao = const LatLng(-21.1355, -44.2616); // Fallback
  Set<Marker> _marcadoresSupabase = {};

  // Nova variável para guardar o local clicado manualmente
  LatLng? _localSelecionado;

  bool _carregandoLocalizacao = true;

  @override
  void initState() {
    super.initState();
    _inicializarMapa();
  }

  Future<void> _inicializarMapa() async {
    await _obterLocalizacaoAtual();
    await _carregarAlertas();
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

  Future<void> _carregarAlertas() async {
    try {
      final resposta = await supabase.from('danger_reports').select();

      Set<Marker> marcadores = {};

      for (var alerta in resposta) {
        marcadores.add(
          Marker(
            markerId: MarkerId(alerta['id'].toString()),
            position: LatLng(alerta['latitude'], alerta['longitude']),
            infoWindow: InfoWindow(
              title: alerta['tipo_perigo']
                  .toString()
                  .replaceAll('_', ' ')
                  .toUpperCase(),
              snippet: alerta['descricao'] ?? 'Sem descrição',
            ),
            icon: BitmapDescriptor.defaultMarkerWithHue(
              BitmapDescriptor.hueRed,
            ),
          ),
        );
      }

      setState(() {
        _marcadoresSupabase = marcadores;
      });
    } catch (e) {
      debugPrint('Erro ao carregar alertas: $e');
    }
  }

  // Combina os alertas do banco com o pino manual (se houver)
  Set<Marker> get _todosOsMarcadores {
    final marcadores = Set<Marker>.from(_marcadoresSupabase);

    if (_localSelecionado != null) {
      marcadores.add(
        Marker(
          markerId: const MarkerId('pino_manual'),
          position: _localSelecionado!,
          icon: BitmapDescriptor.defaultMarkerWithHue(
            BitmapDescriptor.hueBlue,
          ), // Pino Azul
          infoWindow: const InfoWindow(
            title: 'Local Selecionado',
            snippet: 'Relatar risco aqui',
          ),
        ),
      );
    }

    return marcadores;
  }

  Future<void> _salvarAlerta(
    String categoriaVisual,
    String descricao,
    bool isAnonimo,
  ) async {
    final user = supabase.auth.currentUser;

    String tipoBanco = 'area_deserta';
    if (categoriaVisual == 'Assédio') tipoBanco = 'assedio';
    if (categoriaVisual == 'Iluminação ruim') tipoBanco = 'iluminacao_ruim';
    if (categoriaVisual == 'Perseguição') tipoBanco = 'perseguicao';
    if (categoriaVisual == 'Local suspeito') tipoBanco = 'area_deserta';

    try {
      double lat;
      double lng;

      if (_localSelecionado != null) {
        lat = _localSelecionado!.latitude;
        lng = _localSelecionado!.longitude;
      } else {
        Position posicao = await Geolocator.getCurrentPosition();
        lat = posicao.latitude;
        lng = posicao.longitude;
      }

      // --- INÍCIO DA LÓGICA HÍBRIDA DE ENDEREÇO ---
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
          List<Placemark> placemarks = await placemarkFromCoordinates(lat, lng);
          if (placemarks.isNotEmpty) {
            Placemark place = placemarks[0];
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
      // --- FIM DA LÓGICA HÍBRIDA DE ENDEREÇO ---

      // Lógica do anonimato: se for anônimo, passamos null. Se não, passamos o id do usuário logado.
      final idParaSalvar = isAnonimo ? null : user?.id;

      await supabase.from('danger_reports').insert({
        'usuario_id': idParaSalvar,
        'tipo_perigo': tipoBanco,
        'descricao': descricao.isEmpty ? null : descricao,
        'latitude': lat,
        'longitude': lng,
        'endereco': enderecoDescoberto, // <-- Salvando o endereço direto no BD!
      });

      setState(() {
        _localSelecionado = null;
      });

      _carregarAlertas();

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

  void _abrirModalRisco(BuildContext context) {
    setState(() {
      _modalAberto = true;
    });

    String? categoriaSelecionada;
    final descricaoController = TextEditingController();
    bool relatoAnonimo = false;

    // Texto dinâmico para avisar a usuária de onde o alerta está vindo
    String textoOrigemLocal = _localSelecionado != null
        ? '📍 Local selecionado manualmente no mapa'
        : '📡 Sua localização atual (GPS)';

    String textoBotao = _localSelecionado != null
        ? 'Registrar neste local'
        : 'Registrar com meu GPS';

    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      isScrollControlled: true,
      builder: (context) {
        return StatefulBuilder(
          builder: (BuildContext context, StateSetter setModalState) {
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

                  // Mostra de onde vem a localização
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

                  // --- Botão de Anonimato ---
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
            markers: _todosOsMarcadores,
            myLocationEnabled: true,
            myLocationButtonEnabled: true,
            zoomControlsEnabled: false,
            onTap: (LatLng position) {
              // Se o modal estiver aberto, ignora o clique no mapa!
              if (_modalAberto) return;

              setState(() {
                _localSelecionado = position;
              });
            },
          ),

          if (_carregandoLocalizacao)
            const Center(child: CircularProgressIndicator()),

          // Botãozinho para limpar o pino manual caso a usuária desista
          if (_localSelecionado != null)
            Positioned(
              bottom: 96,
              right: 24,
              child: FloatingActionButton.small(
                heroTag: 'clear_btn',
                backgroundColor: Colors.white,
                onPressed: () => setState(() => _localSelecionado = null),
                child: const Icon(Icons.close, color: Colors.black54),
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
        ],
      ),
    );
  }
}
