# Relatório de avaliação dos LLMs

Gerado em 2026-11-03T04:00:16.422938+00:00.

Gabarito: 120 posts anotados manualmente (`ground_truth.jsonl`). Métricas multiclasse sobre `tipo_perigo`; métricas binárias sobre `relevante`. `iluminacao_ruim` tem suporte 0 no gabarito e fica fora do macro-F1.

## Visão geral

| Modelo | Modo | Avaliados | Cobertura | Acurácia tipo | Macro-F1 | Acurácia alerta | Precisão alerta | Recall alerta | F1 alerta | JSON inválido | Schema inválido |
|---|---|---|---|---|---|---|---|---|---|---|---|
| deepseek/deepseek-flash | few_shot | 120 | 120/120 | 0.917 | 0.915 | 0.950 | 0.927 | 0.962 | 0.944 | 0 | 0 |
| gemini/gemini-3.1-flash-lite | few_shot | 120 | 120/120 | 0.892 | 0.875 | 0.933 | 0.881 | 0.981 | 0.929 | 0 | 0 |
| ollama/qwen3:8b | few_shot | 120 | 120/120 | 0.917 | 0.889 | 0.942 | 0.960 | 0.906 | 0.932 | 0 | 0 |

## Custo e latência

| Modelo | Latência média | Mediana | p95 | Máx. | Custo total | Custo/item |
|---|---|---|---|---|---|---|
| deepseek/deepseek-flash | 2.784 s | 2.065 s | 4.954 s | 14.730 s | US$ 0.000000 | US$ 0.000000 |
| gemini/gemini-3.1-flash-lite | 3.904 s | 3.861 s | 5.816 s | 12.501 s | US$ 0.000000 | US$ 0.000000 |
| ollama/qwen3:8b | 12.066 s | 13.083 s | 18.414 s | 21.314 s | US$ 0.000000 | US$ 0.000000 |

> Custo 0,000000 indica que o provedor não reportou tokens/custo (a API local de sessões do OpenCode devolve apenas o texto). Não interprete como gratuito.

## Métricas por classe

### deepseek/deepseek-flash

Macro-F1 = 0.915 em 12 classes com suporte ≥ 1. `iluminacao_ruim` tem suporte 0 e não entra no macro-F1.

| Classe | Suporte | Previsto | Precisão | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|---|---|
| `assedio` | 2 | 2 | 1.000 | 1.000 | 1.000 | 2 | 0 | 0 |
| `iluminacao_ruim` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `perseguicao` | 3 | 3 | 1.000 | 1.000 | 1.000 | 3 | 0 | 0 |
| `local_suspeito` | 3 | 3 | 0.667 | 0.667 | 0.667 | 2 | 1 | 1 |
| `acidente_transito` | 4 | 4 | 1.000 | 1.000 | 1.000 | 4 | 0 | 0 |
| `assalto` | 6 | 6 | 1.000 | 1.000 | 1.000 | 6 | 0 | 0 |
| `furto` | 4 | 4 | 1.000 | 1.000 | 1.000 | 4 | 0 | 0 |
| `violencia_fisica` | 7 | 6 | 0.833 | 0.714 | 0.769 | 5 | 1 | 2 |
| `presenca_arma` | 5 | 6 | 0.833 | 1.000 | 0.909 | 5 | 1 | 0 |
| `incendio_fumaca` | 6 | 6 | 1.000 | 1.000 | 1.000 | 6 | 0 | 0 |
| `via_bloqueada` | 3 | 4 | 0.750 | 1.000 | 0.857 | 3 | 1 | 0 |
| `emergencia_medica` | 11 | 15 | 0.733 | 1.000 | 0.846 | 11 | 4 | 0 |
| `nenhum` | 66 | 61 | 0.967 | 0.894 | 0.929 | 59 | 2 | 7 |

### gemini/gemini-3.1-flash-lite

Macro-F1 = 0.875 em 12 classes com suporte ≥ 1. `iluminacao_ruim` tem suporte 0 e não entra no macro-F1.

| Classe | Suporte | Previsto | Precisão | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|---|---|
| `assedio` | 2 | 2 | 1.000 | 1.000 | 1.000 | 2 | 0 | 0 |
| `iluminacao_ruim` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `perseguicao` | 3 | 3 | 1.000 | 1.000 | 1.000 | 3 | 0 | 0 |
| `local_suspeito` | 3 | 6 | 0.500 | 1.000 | 0.667 | 3 | 3 | 0 |
| `acidente_transito` | 4 | 2 | 1.000 | 0.500 | 0.667 | 2 | 0 | 2 |
| `assalto` | 6 | 6 | 1.000 | 1.000 | 1.000 | 6 | 0 | 0 |
| `furto` | 4 | 3 | 1.000 | 0.750 | 0.857 | 3 | 0 | 1 |
| `violencia_fisica` | 7 | 4 | 1.000 | 0.571 | 0.727 | 4 | 0 | 3 |
| `presenca_arma` | 5 | 6 | 0.833 | 1.000 | 0.909 | 5 | 1 | 0 |
| `incendio_fumaca` | 6 | 6 | 1.000 | 1.000 | 1.000 | 6 | 0 | 0 |
| `via_bloqueada` | 3 | 3 | 1.000 | 1.000 | 1.000 | 3 | 0 | 0 |
| `emergencia_medica` | 11 | 19 | 0.579 | 1.000 | 0.733 | 11 | 8 | 0 |
| `nenhum` | 66 | 60 | 0.983 | 0.894 | 0.936 | 59 | 1 | 7 |

### ollama/qwen3:8b

Macro-F1 = 0.889 em 12 classes com suporte ≥ 1. `iluminacao_ruim` tem suporte 0 e não entra no macro-F1.

| Classe | Suporte | Previsto | Precisão | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|---|---|
| `assedio` | 2 | 2 | 1.000 | 1.000 | 1.000 | 2 | 0 | 0 |
| `iluminacao_ruim` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `perseguicao` | 3 | 3 | 1.000 | 1.000 | 1.000 | 3 | 0 | 0 |
| `local_suspeito` | 3 | 4 | 0.500 | 0.667 | 0.571 | 2 | 2 | 1 |
| `acidente_transito` | 4 | 4 | 1.000 | 1.000 | 1.000 | 4 | 0 | 0 |
| `assalto` | 6 | 5 | 1.000 | 0.833 | 0.909 | 5 | 0 | 1 |
| `furto` | 4 | 4 | 0.750 | 0.750 | 0.750 | 3 | 1 | 1 |
| `violencia_fisica` | 7 | 4 | 1.000 | 0.571 | 0.727 | 4 | 0 | 3 |
| `presenca_arma` | 5 | 6 | 0.833 | 1.000 | 0.909 | 5 | 1 | 0 |
| `incendio_fumaca` | 6 | 6 | 1.000 | 1.000 | 1.000 | 6 | 0 | 0 |
| `via_bloqueada` | 3 | 3 | 1.000 | 1.000 | 1.000 | 3 | 0 | 0 |
| `emergencia_medica` | 11 | 10 | 0.900 | 0.818 | 0.857 | 9 | 1 | 2 |
| `nenhum` | 66 | 69 | 0.927 | 0.970 | 0.948 | 64 | 5 | 2 |

## Matriz de confusão

### deepseek/deepseek-flash

Linhas = gabarito; colunas = previsto. Só linhas/colunas com ocorrência.

| gabarito \ previsto | `assedio` | `perseguicao` | `local_suspeito` | `acidente_transito` | `assalto` | `furto` | `violencia_fisica` | `presenca_arma` | `incendio_fumaca` | `via_bloqueada` | `emergencia_medica` | `nenhum` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `assedio` | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `perseguicao` | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `local_suspeito` | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `acidente_transito` | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `assalto` | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `furto` | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 |
| `violencia_fisica` | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 1 | 1 |
| `presenca_arma` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 |
| `incendio_fumaca` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 |
| `via_bloqueada` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 |
| `emergencia_medica` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 11 | 0 |
| `nenhum` | 0 | 0 | 1 | 0 | 0 | 0 | 1 | 1 | 0 | 1 | 3 | 59 |

### gemini/gemini-3.1-flash-lite

Linhas = gabarito; colunas = previsto. Só linhas/colunas com ocorrência.

| gabarito \ previsto | `assedio` | `perseguicao` | `local_suspeito` | `acidente_transito` | `assalto` | `furto` | `violencia_fisica` | `presenca_arma` | `incendio_fumaca` | `via_bloqueada` | `emergencia_medica` | `nenhum` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `assedio` | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `perseguicao` | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `local_suspeito` | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `acidente_transito` | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 |
| `assalto` | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `furto` | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 1 |
| `violencia_fisica` | 0 | 0 | 1 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 2 | 0 |
| `presenca_arma` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 |
| `incendio_fumaca` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 |
| `via_bloqueada` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 |
| `emergencia_medica` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 11 | 0 |
| `nenhum` | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 4 | 59 |

### ollama/qwen3:8b

Linhas = gabarito; colunas = previsto. Só linhas/colunas com ocorrência.

| gabarito \ previsto | `assedio` | `perseguicao` | `local_suspeito` | `acidente_transito` | `assalto` | `furto` | `violencia_fisica` | `presenca_arma` | `incendio_fumaca` | `via_bloqueada` | `emergencia_medica` | `nenhum` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `assedio` | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `perseguicao` | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `local_suspeito` | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `acidente_transito` | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `assalto` | 0 | 0 | 0 | 0 | 5 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| `furto` | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 1 |
| `violencia_fisica` | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 1 | 0 | 0 | 1 | 1 |
| `presenca_arma` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 |
| `incendio_fumaca` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 |
| `via_bloqueada` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 |
| `emergencia_medica` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 | 2 |
| `nenhum` | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 64 |

## Área de cobertura

O gabarito tem 6 itens fora da área (1 com tipo de evento). Alertar um item fora da área é falso positivo operacional.

| Modelo | Fora no gabarito | Fora previsto | Acerto fora | Alertados fora | IDs |
|---|---|---|---|---|---|
| deepseek/deepseek-flash | 6 | 5 | 0.975 | 0 | — |
| gemini/gemini-3.1-flash-lite | 6 | 9 | 0.975 | 0 | — |
| ollama/qwen3:8b | 6 | 5 | 0.992 | 0 | — |

## Endereço

Comparação textual normalizada (sem geocodificação), restrita aos itens com endereço no gabarito. `exato`/`contém`/`fuzzy` contam falta de endereço previsto como erro.

| Modelo | Itens com endereço no gabarito | Exato | Contém | Fuzzy | Fuzzy (ambos) | Endereço previsto sem GT |
|---|---|---|---|---|---|---|
| deepseek/deepseek-flash | 64 | 0.109 | 0.812 | 0.844 | 0.857 | 39 |
| gemini/gemini-3.1-flash-lite | 64 | 0.031 | 0.781 | 0.688 | 0.688 | 38 |
| ollama/qwen3:8b | 64 | 0.047 | 0.703 | 0.625 | 0.635 | 9 |

## Intervalo de confiança (bootstrap)

1000 reamostragens por modelo, IC de 95%. Útil para não superinterpretar diferenças pequenas em 120 itens.

| Modelo | Acurácia tipo (IC 95%) | Macro-F1 (IC 95%) | Acurácia alerta (IC 95%) |
|---|---|---|---|
| deepseek/deepseek-flash | 0.867–0.958 | 0.839–0.965 | 0.908–0.983 |
| gemini/gemini-3.1-flash-lite | 0.833–0.942 | 0.776–0.935 | 0.883–0.975 |
| ollama/qwen3:8b | 0.867–0.958 | 0.798–0.947 | 0.900–0.983 |

## Comparação pareada

Modelos reavaliados nos 120 itens respondidos por todos. É a comparação mais justa quando a cobertura difere.

| Modelo | N | Acurácia tipo | Macro-F1 | Acurácia alerta | Precisão alerta | Recall alerta | F1 alerta |
|---|---|---|---|---|---|---|---|
| deepseek/deepseek-flash | 120 | 0.917 | 0.915 | 0.950 | 0.927 | 0.962 | 0.944 |
| gemini/gemini-3.1-flash-lite | 120 | 0.892 | 0.875 | 0.933 | 0.881 | 0.981 | 0.929 |
| ollama/qwen3:8b | 120 | 0.917 | 0.889 | 0.942 | 0.960 | 0.906 | 0.932 |

## Erros por modelo

### deepseek/deepseek-flash

- Erros de tipo: 10; erros de alerta: 6; falhas: 0; JSON inválido: 0; schema inválido: 0.

| ID | Gabarito | Previsto | Confiança | Alerta gabarito | Alerta previsto |
|---|---|---|---|---|---|
| sjd-031 | `violencia_fisica` | `nenhum` | 0.800 | True | False |
| sjd-033 | `nenhum` | `emergencia_medica` | 0.550 | False | True |
| sjd-064 | `local_suspeito` | `nenhum` | 0.800 | True | False |
| sjd-073 | `violencia_fisica` | `emergencia_medica` | 0.850 | True | True |
| sjd-074 | `nenhum` | `emergencia_medica` | 0.600 | False | True |
| sjd-077 | `nenhum` | `presenca_arma` | 0.550 | False | False |
| sjd-082 | `nenhum` | `violencia_fisica` | 0.600 | False | False |
| sjd-083 | `nenhum` | `via_bloqueada` | 0.600 | False | False |
| sjd-088 | `nenhum` | `local_suspeito` | 0.850 | False | True |
| sjd-098 | `nenhum` | `emergencia_medica` | 0.750 | False | True |

### gemini/gemini-3.1-flash-lite

- Erros de tipo: 13; erros de alerta: 8; falhas: 0; JSON inválido: 0; schema inválido: 0.

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
| sjd-109 | `nenhum` | `emergencia_medica` | 0.950 | False | True |

### ollama/qwen3:8b

- Erros de tipo: 10; erros de alerta: 7; falhas: 0; JSON inválido: 0; schema inválido: 0.

| ID | Gabarito | Previsto | Confiança | Alerta gabarito | Alerta previsto |
|---|---|---|---|---|---|
| sjd-001 | `nenhum` | `local_suspeito` | 0.900 | False | True |
| sjd-002 | `violencia_fisica` | `presenca_arma` | 0.950 | True | True |
| sjd-015 | `emergencia_medica` | `nenhum` | 0.800 | True | False |
| sjd-029 | `emergencia_medica` | `nenhum` | 0.850 | True | False |
| sjd-031 | `violencia_fisica` | `nenhum` | 0.950 | True | False |
| sjd-051 | `local_suspeito` | `nenhum` | 0.950 | True | False |
| sjd-071 | `furto` | `nenhum` | 0.950 | True | False |
| sjd-073 | `violencia_fisica` | `emergencia_medica` | 0.950 | True | True |
| sjd-088 | `nenhum` | `local_suspeito` | 0.900 | False | True |
| sjd-089 | `assalto` | `furto` | 0.850 | True | True |

## Arquivos avaliados

- `deepseek_flash_compact.jsonl` — modelo `deepseek/deepseek-flash`, modo `few_shot`.
- `gemini_3_1_flash_lite_compact.jsonl` — modelo `gemini/gemini-3.1-flash-lite`, modo `few_shot`.
- `ollama_qwen3_8b_compact.jsonl` — modelo `ollama/qwen3:8b`, modo `few_shot`.
