import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

/// Resultado do envio do alerta à polícia.
class PoliceAlertResult {
  final bool policeAlerted;
  final String title;
  final String message;
  final DateTime timestamp;

  PoliceAlertResult({
    required this.policeAlerted,
    required this.title,
    required this.message,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();
}

/// Serviço para integração com o Banco de Vítimas Reincidentes (tabela `recurring_victims` no Supabase)
/// e acionamento da Polícia Militar (190) em situações de emergência.
class PoliceAlertService {
  PoliceAlertService._privateConstructor();
  static final PoliceAlertService instance = PoliceAlertService._privateConstructor();

  // Memória local de reserva para testes offline ou antes de aplicar as tabelas no banco
  final Set<String> _bancoVitimasReincidentesMock = {
    '12345678900',
    '11122233344',
    '00000000000',
    '99988877766',
  };

  /// Sanitiza o CPF removendo qualquer caractere não numérico.
  String _limparCpf(String? cpf) {
    if (cpf == null) return '';
    return cpf.replaceAll(RegExp(r'\D'), '');
  }

  /// Verifica se o CPF fornecido está cadastrado na tabela `recurring_victims` do Supabase.
  /// Se o Supabase falhar ou a tabela não existir ainda, utiliza a lista local como fallback.
  Future<bool> isCpfCadastradoNoBanco(String? cpf) async {
    final cpfLimpo = _limparCpf(cpf);
    if (cpfLimpo.isEmpty) return false;

    try {
      final supabase = Supabase.instance.client;
      final res = await supabase
          .from('recurring_victims')
          .select('id, ativo')
          .eq('cpf', cpfLimpo)
          .maybeSingle();

      if (res != null) {
        final bool ativo = res['ativo'] ?? true;
        return ativo;
      }
    } catch (e) {
      debugPrint('[PoliceAlertService] Consulta à tabela recurring_victims no Supabase falhou: $e. Usando fallback local.');
    }

    return _bancoVitimasReincidentesMock.contains(cpfLimpo);
  }

  /// Adiciona ou remove um CPF na tabela `recurring_victims` do Supabase para simulações/testes.
  Future<bool> alternarCpfNoBanco(String cpf, String nomeUsuaria) async {
    final cpfLimpo = _limparCpf(cpf);
    if (cpfLimpo.isEmpty) return false;

    final atualmenteCadastrado = await isCpfCadastradoNoBanco(cpfLimpo);

    try {
      final supabase = Supabase.instance.client;
      if (atualmenteCadastrado) {
        await supabase.from('recurring_victims').delete().eq('cpf', cpfLimpo);
        _bancoVitimasReincidentesMock.remove(cpfLimpo);
        return false;
      } else {
        await supabase.from('recurring_victims').upsert({
          'cpf': cpfLimpo,
          'nome_completo': nomeUsuaria,
          'observacoes': 'Cadastrada via aplicativo',
          'ativo': true,
        });
        _bancoVitimasReincidentesMock.add(cpfLimpo);
        return true;
      }
    } catch (e) {
      debugPrint('[PoliceAlertService] Alternar CPF no Supabase falhou: $e');
      if (atualmenteCadastrado) {
        _bancoVitimasReincidentesMock.remove(cpfLimpo);
        return false;
      } else {
        _bancoVitimasReincidentesMock.add(cpfLimpo);
        return true;
      }
    }
  }

  /// Simula o acionamento e envio do alerta para a Polícia Militar (190).
  /// O alerta só é efetivamente disparado se a usuária possuir CPF cadastrado no banco.
  Future<PoliceAlertResult> alertarPolicia({
    required String nomeUsuaria,
    required String? cpf,
    double? lat,
    double? lng,
  }) async {
    final isReincidente = await isCpfCadastradoNoBanco(cpf);

    if (!isReincidente) {
      debugPrint('[PoliceAlertService] Polícia NÃO notificada: CPF ($cpf) não consta no banco de vítimas reincidentes.');
      return PoliceAlertResult(
        policeAlerted: false,
        title: 'Polícia Não Notificada',
        message: 'O CPF informado não está registrado no banco de vítimas reincidentes.',
      );
    }

    // Simula latência de rede/despacho do serviço policial
    await Future.delayed(const Duration(milliseconds: 500));

    final localizacaoStr = (lat != null && lng != null)
        ? 'https://www.google.com/maps?q=$lat,$lng ($lat, $lng)'
        : 'Localização indisponível';

    debugPrint('===========================================================');
    debugPrint('🚨 [POLÍCIA MILITAR 190] ALERTA ENVIADO À POLÍCIA MILITAR! 🚨');
    debugPrint('   Usuária: $nomeUsuaria');
    debugPrint('   CPF: $cpf');
    debugPrint('   Status: VÍTIMA REINCIDENTE CADASTRADA (recurring_victims)');
    debugPrint('   Localização: $localizacaoStr');
    debugPrint('   Ação: Despacho prioritário de viatura acionado.');
    debugPrint('===========================================================');

    return PoliceAlertResult(
      policeAlerted: true,
      title: '🚨 Polícia Militar (190) Notificada',
      message: 'Vítima reincidente identificada por CPF. Alerta enviado à Polícia Militar (190) com prioridade máxima.',
    );
  }
}
