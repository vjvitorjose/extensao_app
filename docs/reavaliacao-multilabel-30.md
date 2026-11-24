# Reavaliação multi-rótulo — DeepSeek Flash × Qwen3 8B

**Data:** 24/11/2026  
**Amostra:** 30 itens (15 Facebook, 15 Emboabas)  
**Gabarito:** `scripts/ground_truth_consenso_90.csv`  
**Prompt:** multi-rótulo, 18 categorias + `nenhum`, 21 exemplos few-shot sintéticos  
**Modelos:** `deepseek/deepseek-flash` (OpenCode) e `ollama/qwen3:8b` (local)

> O arquivo do gabarito se chama `consenso_90`, mas contém **30 itens**. Desses,
> 23 são `nenhum` e apenas 7 têm alguma categoria. Os números abaixo são
> exploratórios e não estimam desempenho em produção.

## 1. Resultado bruto

| Modelo | Exact match | Hamming | Micro P | Micro R | Micro F1 | Macro F1 | Saída válida | Latência média |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DeepSeek Flash | **0,833** | **0,012** | **0,938** | **0,857** | **0,896** | **0,773** | **30/30** | 2,50 s |
| Qwen3 8B | 0,800 | 0,025 | 0,839 | 0,743 | 0,788 | 0,474 | 28/30 | 6,57 s |

O Qwen teve 2 respostas com schema inválido (`indicadores` com valor fora da
lista). Os rótulos dessas respostas foram preservados; a falha conta apenas em
“saída válida”.

## 2. Por categoria

| Categoria | Suporte | DeepSeek P/R/F1 | Qwen P/R/F1 |
|---|---:|---|---|
| `nenhum` | 23 | 1,00 / 0,91 / 0,95 | 0,95 / 0,91 / 0,93 |
| `presenca_arma` | 2 | 1,00 / 1,00 / 1,00 | 1,00 / 0,50 / 0,67 |
| `acidente_transito` | 2 | 1,00 / 1,00 / 1,00 | 1,00 / 1,00 / 1,00 |
| `emergencia_medica` | 2 | 1,00 / 1,00 / 1,00 | 1,00 / 0,50 / 0,67 |
| `violencia_fisica` | 2 | — / 0,00 / 0,00 | — / 0,00 / 0,00 |
| `homicidio` | 1 | 1,00 / 1,00 / 1,00 | — / 0,00 / 0,00 |
| `assalto` | 1 | 1,00 / 1,00 / 1,00 | — / 0,00 / 0,00 |
| `perseguicao` | 1 | 0,00 / 0,00 / 0,00 | 0,00 / 0,00 / 0,00 |
| `trafico` | 1 | 1,00 / 1,00 / 1,00 | 1,00 / 1,00 / 1,00 |
| `latrocinio` | 0 | — | 0,00 (1 FP) |
| `furto` | 0 | — | 0,00 (1 FP) |
| `local_suspeito` | 0 | 0,00 (1 FP) | 0,00 (1 FP) |

Macro-F1 é instável aqui: há classes com suporte 1–2, então um único acerto ou
erro move o número em 10–20 pontos.

## 3. Concordância entre os modelos

- Exact match: **0,900**
- Jaccard médio: **0,900**
- Divergência em 3 itens: um composto (`latrocinio`), um `assalto` × `furto` e
  um caso de `homicidio` ausente no Qwen.

## 4. Divergências e revisão do gabarito

| Item | Gabarito | DeepSeek | Qwen | Leitura |
|---|---|---|---|---|
| `emboabas-1019c1f4b0f1` | homicidio; presenca_arma; violencia_fisica | homicidio; presenca_arma | **latrocinio** | Segurança morto a tiros em festa, sem roubo. Qwen erra o composto; o gabarito repete `violencia_fisica`, que a própria regra manda remover. DeepSeek está mais correto. |
| `emboabas-1638cf6dd91f` | emergencia_medica | emergencia_medica | **nenhum** | Bombeiros resgatam homem perdido na serra. Falso negativo claro do Qwen. |
| `emboabas-8a0605605e15` | nenhum | perseguicao | perseguicao | Fuga de abordagem policial em alta velocidade. A definição da taxonomia inclui perseguição policial com risco viário — **os dois modelos parecem certos e o gabarito, errado**. |
| `emboabas-9d50a110b2f6` | presenca_arma; perseguicao | presenca_arma | presenca_arma | Ex-namorado atira contra a casa. `perseguicao` é discutível; os dois modelos omitem o segundo rótulo. |
| `emboabas-b97d284ab5d4` | assalto; violencia_fisica | assalto | **furto** | O texto alterna “roubo” e “furto”; a vítima é quem aplica o golpe. `violencia_fisica` no gabarito não tem apoio. Caso genuinamente ambíguo entre assalto e furto. |
| `facebook-eb188d51fea6` | nenhum | local_suspeito | local_suspeito | Descarte irregular de lixo com risco sanitário em local identificável. A definição de `local_suspeito` inclui risco sanitário — **os modelos parecem certos e o gabarito, discutível**. |

## 5. Sensibilidade ao gabarito

Como 3–4 itens do gabarito são questionáveis, recalculei cenários:

| Cenário | DeepSeek exact / micro / macro | Qwen exact / micro / macro |
|---|---|---|
| A. Gabarito como recebido | 0,833 / 0,896 / 0,773 | 0,800 / 0,788 / 0,474 |
| B. Corrige `1019`, `8a06`, `eb18` | **0,933 / 0,970 / 0,867** | 0,867 / 0,862 / 0,598 |
| C. B + `b97d` vira `furto` | 0,933 / 0,954 / 0,852 | **0,900 / 0,906 / 0,775** |
| D. B + remove `perseguicao` do `9d50` | **0,967 / 0,985 / 0,900** | 0,900 / 0,875 / 0,631 |

A conclusão qualitativa se mantém: DeepSeek é melhor, mas o tamanho da vantagem
depende de decisões de anotação que ainda não estão fechadas.

## 6. Limitações

- 30 itens, 23 negativos: qualquer métrica macro é frágil.
- O gabarito não tem `fora_da_area` nem `relevante`; as métricas binárias de
  área não são interpretáveis (o script assumiu `false`).
- O gabarito viola a precedência de compostos em pelo menos um item
  (`homicidio` + `violencia_fisica`).
- Apenas um arquivo de consenso, sem as três fichas originais nem relatório de
  divergência humana.
- O prompt few-shot é sintético e nenhum item da amostra foi usado nele.

## 7. Recomendação

1. Revisar e adjudicar os 6 itens da seção 4 antes de tratar o gabarito como
   definitivo.
2. Completar a amostra para os 90 itens previstos, mantendo o equilíbrio entre
   fontes e incluindo mais positivos.
3. Reexecutar os dois modelos depois da adjudicação; com 30 itens, a diferença
   entre eles é menor que a incerteza do gabarito.
4. Manter o DeepSeek como referência de qualidade e o Qwen como opção local de
   custo zero, mas tratar o erro de composto do Qwen (`latrocinio` em homicídio
   sem roubo) como risco conhecido.

## 8. Arquivos

- `scripts/data/eval/study_multilabel/sample30.jsonl` — amostra reconstruída.
- `scripts/data/eval/study_multilabel/ground_truth_sample30.jsonl` — gabarito convertido para JSONL.
- `scripts/data/eval/study_multilabel/runs_sample30/` — respostas brutas.
- `scripts/data/eval/study_multilabel/metrics_sample30.json` — métricas completas.
- `scripts/ground_truth_consenso_90.csv` — gabarito original.
