# Relatório de avaliação dos LLMs

Gerado em 2026-11-03T03:45:06.651369+00:00.

Gabarito: 120 posts anotados manualmente (`ground_truth.jsonl`). Métricas multiclasse sobre `tipo_perigo`; métricas binárias sobre `relevante`. `iluminacao_ruim` tem suporte 0 no gabarito e fica fora do macro-F1.

## Visão geral

| Modelo | Modo | Avaliados | Cobertura | Acurácia tipo | Macro-F1 | Acurácia alerta | Precisão alerta | Recall alerta | F1 alerta | JSON inválido | Schema inválido |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gemini/gemini-3.1-flash-lite | few_shot | 106 | 106/120 | 0.887 | 0.869 | 0.934 | 0.880 | 0.978 | 0.926 | 0 | 0 |

## Custo e latência

| Modelo | Latência média | Mediana | p95 | Máx. | Custo total | Custo/item |
|---|---|---|---|---|---|---|
| gemini/gemini-3.1-flash-lite | 3.866 s | 3.777 s | 5.908 s | 12.501 s | US$ 0.000000 | US$ 0.000000 |

## Métricas por classe

### gemini/gemini-3.1-flash-lite

Macro-F1 = 0.869 em 12 classes com suporte ≥ 1. `iluminacao_ruim` tem suporte 0 e não entra no macro-F1.

| Classe | Suporte | Previsto | Precisão | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|---|---|
| `assedio` | 2 | 2 | 1.000 | 1.000 | 1.000 | 2 | 0 | 0 |
| `iluminacao_ruim` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `perseguicao` | 2 | 2 | 1.000 | 1.000 | 1.000 | 2 | 0 | 0 |
| `local_suspeito` | 3 | 6 | 0.500 | 1.000 | 0.667 | 3 | 3 | 0 |
| `acidente_transito` | 4 | 2 | 1.000 | 0.500 | 0.667 | 2 | 0 | 2 |
| `assalto` | 3 | 3 | 1.000 | 1.000 | 1.000 | 3 | 0 | 0 |
| `furto` | 4 | 3 | 1.000 | 0.750 | 0.857 | 3 | 0 | 1 |
| `violencia_fisica` | 6 | 3 | 1.000 | 0.500 | 0.667 | 3 | 0 | 3 |
| `presenca_arma` | 4 | 5 | 0.800 | 1.000 | 0.889 | 4 | 1 | 0 |
| `incendio_fumaca` | 6 | 6 | 1.000 | 1.000 | 1.000 | 6 | 0 | 0 |
| `via_bloqueada` | 2 | 2 | 1.000 | 1.000 | 1.000 | 2 | 0 | 0 |
| `emergencia_medica` | 10 | 17 | 0.588 | 1.000 | 0.741 | 10 | 7 | 0 |
| `nenhum` | 60 | 55 | 0.982 | 0.900 | 0.939 | 54 | 1 | 6 |

## Matriz de confusão

### gemini/gemini-3.1-flash-lite

Linhas = gabarito; colunas = previsto. Só linhas/colunas com ocorrência.

| gabarito \ previsto | `assedio` | `perseguicao` | `local_suspeito` | `acidente_transito` | `assalto` | `furto` | `violencia_fisica` | `presenca_arma` | `incendio_fumaca` | `via_bloqueada` | `emergencia_medica` | `nenhum` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `assedio` | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `perseguicao` | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `local_suspeito` | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `acidente_transito` | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 |
| `assalto` | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `furto` | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 1 |
| `violencia_fisica` | 0 | 0 | 1 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 2 | 0 |
| `presenca_arma` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 |
| `incendio_fumaca` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 |
| `via_bloqueada` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 |
| `emergencia_medica` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10 | 0 |
| `nenhum` | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 3 | 54 |

## Área de cobertura

O gabarito tem 6 itens fora da área (1 com tipo de evento). Alertar um item fora da área é falso positivo operacional.

| Modelo | Fora no gabarito | Fora previsto | Acerto fora | Alertados fora | IDs |
|---|---|---|---|---|---|
| gemini/gemini-3.1-flash-lite | 6 | 9 | 0.972 | 0 | — |

## Endereço

Comparação textual normalizada (sem geocodificação), restrita aos itens com endereço no gabarito. `exato`/`contém`/`fuzzy` contam falta de endereço previsto como erro.

| Modelo | Itens com endereço no gabarito | Exato | Contém | Fuzzy | Fuzzy (ambos) | Endereço previsto sem GT |
|---|---|---|---|---|---|---|
| gemini/gemini-3.1-flash-lite | 54 | 0.037 | 0.759 | 0.685 | 0.685 | 36 |

## Intervalo de confiança (bootstrap)

100 reamostragens por modelo, IC de 95%. Útil para não superinterpretar diferenças pequenas em 120 itens.

| Modelo | Acurácia tipo (IC 95%) | Macro-F1 (IC 95%) | Acurácia alerta (IC 95%) |
|---|---|---|---|
| gemini/gemini-3.1-flash-lite | 0.811–0.943 | 0.755–0.930 | 0.877–0.972 |

## Erros por modelo

### gemini/gemini-3.1-flash-lite

- Erros de tipo: 12; erros de alerta: 7; falhas: 0; JSON inválido: 0; schema inválido: 0.
- Sem registro: 14 itens (sjd-107, sjd-108, sjd-109, sjd-110, sjd-111, sjd-112, sjd-113, sjd-114, sjd-115, sjd-116, sjd-117, sjd-118, sjd-119, sjd-120).

| ID | Gabarito | Previsto | Confiança | Alerta gabarito | Alerta previsto |
|---|---|---|---|---|---|
| sjd-001 | `nenhum` | `local_suspeito` | 0.850 | False | True |
| sjd-010 | `acidente_transito` | `emergencia_medica` | 0.950 | True | True |
| sjd-018 | `acidente_transito` | `emergencia_medica` | 0.950 | True | True |
| sjd-031 | `violencia_fisica` | `local_suspeito` | 0.850 | True | True |
| sjd-033 | `nenhum` | `emergencia_medica` | 0.850 | False | True |
| sjd-042 | `violencia_fisica` | `emergencia_medica` | 0.850 | True | True |
| sjd-052 | `nenhum` | `presenca_arma` | 0.950 | False | True |
| sjd-071 | `furto` | `nenhum` | 0.900 | True | False |
| sjd-073 | `violencia_fisica` | `emergencia_medica` | 0.950 | True | True |
| sjd-074 | `nenhum` | `emergencia_medica` | 0.800 | False | True |
| sjd-088 | `nenhum` | `local_suspeito` | 0.950 | False | True |
| sjd-098 | `nenhum` | `emergencia_medica` | 0.850 | False | True |

## Arquivos avaliados

- `gemini_3_1_flash_lite_compact.jsonl` — modelo `gemini/gemini-3.1-flash-lite`, modo `few_shot`.
