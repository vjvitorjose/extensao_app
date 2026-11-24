# Relatório de avaliação dos LLMs

Gerado em 2026-11-03T03:45:07.886878+00:00.

Gabarito: 120 posts anotados manualmente (`ground_truth.jsonl`). Métricas multiclasse sobre `tipo_perigo`; métricas binárias sobre `relevante`. `iluminacao_ruim` tem suporte 0 no gabarito e fica fora do macro-F1.

## Visão geral

| Modelo | Modo | Avaliados | Cobertura | Acurácia tipo | Macro-F1 | Acurácia alerta | Precisão alerta | Recall alerta | F1 alerta | JSON inválido | Schema inválido |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ollama/qwen3:8b | few_shot | 46 | 46/120 | 0.891 | 0.894 | 0.913 | 0.958 | 0.885 | 0.920 | 0 | 0 |

## Custo e latência

| Modelo | Latência média | Mediana | p95 | Máx. | Custo total | Custo/item |
|---|---|---|---|---|---|---|
| ollama/qwen3:8b | 11.736 s | 11.723 s | 18.106 s | 21.259 s | US$ 0.000000 | US$ 0.000000 |

## Métricas por classe

### ollama/qwen3:8b

Macro-F1 = 0.894 em 12 classes com suporte ≥ 1. `iluminacao_ruim` tem suporte 0 e não entra no macro-F1.

| Classe | Suporte | Previsto | Precisão | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|---|---|
| `assedio` | 2 | 2 | 1.000 | 1.000 | 1.000 | 2 | 0 | 0 |
| `iluminacao_ruim` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `perseguicao` | 1 | 1 | 1.000 | 1.000 | 1.000 | 1 | 0 | 0 |
| `local_suspeito` | 1 | 2 | 0.500 | 1.000 | 0.667 | 1 | 1 | 0 |
| `acidente_transito` | 3 | 3 | 1.000 | 1.000 | 1.000 | 3 | 0 | 0 |
| `assalto` | 1 | 1 | 1.000 | 1.000 | 1.000 | 1 | 0 | 0 |
| `furto` | 2 | 2 | 1.000 | 1.000 | 1.000 | 2 | 0 | 0 |
| `violencia_fisica` | 3 | 1 | 1.000 | 0.333 | 0.500 | 1 | 0 | 2 |
| `presenca_arma` | 3 | 4 | 0.750 | 1.000 | 0.857 | 3 | 1 | 0 |
| `incendio_fumaca` | 3 | 3 | 1.000 | 1.000 | 1.000 | 3 | 0 | 0 |
| `via_bloqueada` | 2 | 2 | 1.000 | 1.000 | 1.000 | 2 | 0 | 0 |
| `emergencia_medica` | 6 | 4 | 1.000 | 0.667 | 0.800 | 4 | 0 | 2 |
| `nenhum` | 19 | 21 | 0.857 | 0.947 | 0.900 | 18 | 3 | 1 |

## Matriz de confusão

### ollama/qwen3:8b

Linhas = gabarito; colunas = previsto. Só linhas/colunas com ocorrência.

| gabarito \ previsto | `assedio` | `perseguicao` | `local_suspeito` | `acidente_transito` | `assalto` | `furto` | `violencia_fisica` | `presenca_arma` | `incendio_fumaca` | `via_bloqueada` | `emergencia_medica` | `nenhum` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `assedio` | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `perseguicao` | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `local_suspeito` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `acidente_transito` | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `assalto` | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `furto` | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| `violencia_fisica` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 |
| `presenca_arma` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 |
| `incendio_fumaca` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 |
| `via_bloqueada` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 |
| `emergencia_medica` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 2 |
| `nenhum` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 18 |

## Área de cobertura

O gabarito tem 6 itens fora da área (1 com tipo de evento). Alertar um item fora da área é falso positivo operacional.

| Modelo | Fora no gabarito | Fora previsto | Acerto fora | Alertados fora | IDs |
|---|---|---|---|---|---|
| ollama/qwen3:8b | 1 | 1 | 1.000 | 0 | — |

## Endereço

Comparação textual normalizada (sem geocodificação), restrita aos itens com endereço no gabarito. `exato`/`contém`/`fuzzy` contam falta de endereço previsto como erro.

| Modelo | Itens com endereço no gabarito | Exato | Contém | Fuzzy | Fuzzy (ambos) | Endereço previsto sem GT |
|---|---|---|---|---|---|---|
| ollama/qwen3:8b | 30 | 0.067 | 0.767 | 0.700 | 0.700 | 3 |

## Intervalo de confiança (bootstrap)

100 reamostragens por modelo, IC de 95%. Útil para não superinterpretar diferenças pequenas em 120 itens.

| Modelo | Acurácia tipo (IC 95%) | Macro-F1 (IC 95%) | Acurácia alerta (IC 95%) |
|---|---|---|---|
| ollama/qwen3:8b | 0.783–0.957 | 0.801–0.979 | 0.848–1.000 |

## Erros por modelo

### ollama/qwen3:8b

- Erros de tipo: 5; erros de alerta: 4; falhas: 0; JSON inválido: 0; schema inválido: 0.
- Sem registro: 74 itens (sjd-047, sjd-048, sjd-049, sjd-050, sjd-051, sjd-052, sjd-053, sjd-054, sjd-055, sjd-056, sjd-057, sjd-058, sjd-059, sjd-060, sjd-061, sjd-062, sjd-063, sjd-064, sjd-065, sjd-066…).

| ID | Gabarito | Previsto | Confiança | Alerta gabarito | Alerta previsto |
|---|---|---|---|---|---|
| sjd-001 | `nenhum` | `local_suspeito` | 0.900 | False | True |
| sjd-002 | `violencia_fisica` | `presenca_arma` | 0.950 | True | True |
| sjd-015 | `emergencia_medica` | `nenhum` | 0.800 | True | False |
| sjd-029 | `emergencia_medica` | `nenhum` | 0.850 | True | False |
| sjd-031 | `violencia_fisica` | `nenhum` | 0.950 | True | False |

## Arquivos avaliados

- `ollama_qwen3_8b_compact.jsonl` — modelo `ollama/qwen3:8b`, modo `few_shot`.
