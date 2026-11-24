# Relatório de avaliação dos LLMs

Gerado em 2026-11-03T03:39:35.314791+00:00.

Gabarito: 120 posts anotados manualmente (`ground_truth.jsonl`). Métricas multiclasse sobre `tipo_perigo`; métricas binárias sobre `relevante`. `iluminacao_ruim` tem suporte 0 no gabarito e fica fora do macro-F1.

## Visão geral

| Modelo | Modo | Avaliados | Cobertura | Acurácia tipo | Macro-F1 | Acurácia alerta | Precisão alerta | Recall alerta | F1 alerta | JSON inválido | Schema inválido |
|---|---|---|---|---|---|---|---|---|---|---|---|
| deepseek/deepseek-flash | few_shot | 120 | 120/120 | 0.917 | 0.915 | 0.950 | 0.927 | 0.962 | 0.944 | 0 | 0 |

## Custo e latência

| Modelo | Latência média | Mediana | p95 | Máx. | Custo total | Custo/item |
|---|---|---|---|---|---|---|
| deepseek/deepseek-flash | 2.784 s | 2.065 s | 4.954 s | 14.730 s | US$ 0.000000 | US$ 0.000000 |

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

## Área de cobertura

O gabarito tem 6 itens fora da área (1 com tipo de evento). Alertar um item fora da área é falso positivo operacional.

| Modelo | Fora no gabarito | Fora previsto | Acerto fora | Alertados fora | IDs |
|---|---|---|---|---|---|
| deepseek/deepseek-flash | 6 | 5 | 0.975 | 0 | — |

## Endereço

Comparação textual normalizada (sem geocodificação), restrita aos itens com endereço no gabarito. `exato`/`contém`/`fuzzy` contam falta de endereço previsto como erro.

| Modelo | Itens com endereço no gabarito | Exato | Contém | Fuzzy | Fuzzy (ambos) | Endereço inventado |
|---|---|---|---|---|---|---|
| deepseek/deepseek-flash | 64 | 0.109 | 0.812 | 0.844 | 0.857 | 39 |

## Intervalo de confiança (bootstrap)

500 reamostragens por modelo, IC de 95%. Útil para não superinterpretar diferenças pequenas em 120 itens.

| Modelo | Acurácia tipo (IC 95%) | Macro-F1 (IC 95%) | Acurácia alerta (IC 95%) |
|---|---|---|---|
| deepseek/deepseek-flash | 0.867–0.958 | 0.835–0.960 | 0.908–0.983 |

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

## Arquivos avaliados

- `deepseek_flash_compact.jsonl` — modelo `deepseek/deepseek-flash`, modo `few_shot`.
