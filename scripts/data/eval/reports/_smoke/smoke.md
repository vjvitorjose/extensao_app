# Relatório de avaliação dos LLMs

Gerado em 2026-11-03T03:14:25.944949+00:00.

Gabarito: 120 posts anotados manualmente (`ground_truth.jsonl`). Métricas multiclasse sobre `tipo_perigo`; métricas binárias sobre `relevante`. `iluminacao_ruim` tem suporte 0 no gabarito e fica fora do macro-F1.

## Visão geral

| Modelo | Modo | Avaliados | Cobertura | Acurácia tipo | Macro-F1 | Acurácia alerta | Precisão alerta | Recall alerta | F1 alerta | JSON inválido | Schema inválido |
|---|---|---|---|---|---|---|---|---|---|---|---|
| opencode/big-pickle | few_shot | 1 | 1/120 | 0.000 | 0.000 | 0.000 | 0.000 | — | 0.000 | 0 | 0 |
| deepseek/deepseek-flash | few_shot | 2 | 2/120 | 1.000 | 1.000 | 1.000 | — | — | — | 0 | 0 |

## Custo e latência

| Modelo | Latência média | Mediana | p95 | Máx. | Custo total | Custo/item |
|---|---|---|---|---|---|---|
| opencode/big-pickle | 13.772 s | 13.772 s | 13.772 s | 13.772 s | US$ 0.000000 | US$ 0.000000 |
| deepseek/deepseek-flash | 5.271 s | 5.271 s | 7.579 s | 7.835 s | US$ 0.000000 | US$ 0.000000 |

> Custo 0,000000 indica que o provedor não reportou tokens/custo (a API local de sessões do OpenCode devolve apenas o texto). Não interprete como gratuito.

## Métricas por classe

### opencode/big-pickle

Macro-F1 = 0.000 em 1 classes com suporte ≥ 1. `iluminacao_ruim` tem suporte 0 e não entra no macro-F1.

| Classe | Suporte | Previsto | Precisão | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|---|---|
| `assedio` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `iluminacao_ruim` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `perseguicao` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `local_suspeito` | 0 | 1 | 0.000 | — | 0.000 | 0 | 1 | 0 |
| `acidente_transito` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `assalto` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `furto` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `violencia_fisica` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `presenca_arma` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `incendio_fumaca` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `via_bloqueada` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `emergencia_medica` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `nenhum` | 1 | 0 | — | 0.000 | 0.000 | 0 | 0 | 1 |

### deepseek/deepseek-flash

Macro-F1 = 1.000 em 2 classes com suporte ≥ 1. `iluminacao_ruim` tem suporte 0 e não entra no macro-F1.

| Classe | Suporte | Previsto | Precisão | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|---|---|
| `assedio` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `iluminacao_ruim` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `perseguicao` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `local_suspeito` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `acidente_transito` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `assalto` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `furto` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `violencia_fisica` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `presenca_arma` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `incendio_fumaca` | 1 | 1 | 1.000 | 1.000 | 1.000 | 1 | 0 | 0 |
| `via_bloqueada` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `emergencia_medica` | 0 | 0 | — | — | — | 0 | 0 | 0 |
| `nenhum` | 1 | 1 | 1.000 | 1.000 | 1.000 | 1 | 0 | 0 |

## Matriz de confusão

### opencode/big-pickle

Linhas = gabarito; colunas = previsto. Só linhas/colunas com ocorrência.

| gabarito \ previsto | `local_suspeito` |
|---|---|
| `nenhum` | 1 |

### deepseek/deepseek-flash

Linhas = gabarito; colunas = previsto. Só linhas/colunas com ocorrência.

| gabarito \ previsto | `incendio_fumaca` | `nenhum` |
|---|---|---|
| `incendio_fumaca` | 1 | 0 |
| `nenhum` | 0 | 1 |

## Área de cobertura

O gabarito tem 6 itens fora da área (1 com tipo de evento). Alertar um item fora da área é falso positivo operacional.

| Modelo | Fora no gabarito | Fora previsto | Acerto fora | Alertados fora | IDs |
|---|---|---|---|---|---|
| opencode/big-pickle | 0 | 0 | 1.000 | 0 | — |
| deepseek/deepseek-flash | 1 | 1 | 1.000 | 0 | — |

## Endereço

Comparação textual normalizada (sem geocodificação), restrita aos itens com endereço no gabarito. `exato`/`contém`/`fuzzy` contam falta de endereço previsto como erro.

| Modelo | Itens com endereço no gabarito | Exato | Contém | Fuzzy | Fuzzy (ambos) | Endereço inventado |
|---|---|---|---|---|---|---|
| opencode/big-pickle | 0 | — | — | — | — | 1 |
| deepseek/deepseek-flash | 1 | 0.000 | 1.000 | 1.000 | 1.000 | 1 |

## Intervalo de confiança (bootstrap)

20 reamostragens por modelo, IC de 95%. Útil para não superinterpretar diferenças pequenas em 120 itens.

| Modelo | Acurácia tipo (IC 95%) | Macro-F1 (IC 95%) | Acurácia alerta (IC 95%) |
|---|---|---|---|
| opencode/big-pickle | 0.000–0.000 | 0.000–0.000 | 0.000–0.000 |
| deepseek/deepseek-flash | 1.000–1.000 | 1.000–1.000 | 1.000–1.000 |

## Comparação pareada

Modelos reavaliados nos 1 itens respondidos por todos. É a comparação mais justa quando a cobertura difere.

| Modelo | N | Acurácia tipo | Macro-F1 | Acurácia alerta | Precisão alerta | Recall alerta | F1 alerta |
|---|---|---|---|---|---|---|---|
| opencode/big-pickle | 1 | 0.000 | 0.000 | 0.000 | 0.000 | — | 0.000 |
| deepseek/deepseek-flash | 1 | 1.000 | 1.000 | 1.000 | — | — | — |

## Erros por modelo

### opencode/big-pickle

- Erros de tipo: 1; erros de alerta: 1; falhas: 1; JSON inválido: 0; schema inválido: 0.
- Sem registro: 118 itens (sjd-002, sjd-003, sjd-004, sjd-005, sjd-006, sjd-007, sjd-008, sjd-009, sjd-010, sjd-011, sjd-013, sjd-014, sjd-015, sjd-016, sjd-017, sjd-018, sjd-019, sjd-020, sjd-021, sjd-022…).

| ID | Gabarito | Previsto | Confiança | Alerta gabarito | Alerta previsto |
|---|---|---|---|---|---|
| sjd-001 | `nenhum` | `local_suspeito` | 0.700 | False | True |

### deepseek/deepseek-flash

- Erros de tipo: 0; erros de alerta: 0; falhas: 0; JSON inválido: 0; schema inválido: 0.
- Sem registro: 118 itens (sjd-002, sjd-003, sjd-004, sjd-005, sjd-006, sjd-007, sjd-008, sjd-009, sjd-010, sjd-011, sjd-013, sjd-014, sjd-015, sjd-016, sjd-017, sjd-018, sjd-019, sjd-020, sjd-021, sjd-022…).

## Arquivos avaliados

- `_smoke_big_pickle.jsonl` — modelo `opencode/big-pickle`, modo `few_shot`.
- `_smoke_deepseek_paid.jsonl` — modelo `deepseek/deepseek-flash`, modo `few_shot`.
