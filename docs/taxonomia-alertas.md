# Taxonomia multi-rótulo e ranking por pena

**Status:** proposta aprovada — fase 1 (taxonomia e ranking) a implementar  
**Data:** 17/11/2026  
**Escopo deste documento:** classificação de alertas de segurança em mais de uma
categoria e ordenação das categorias pela média harmônica da pena prevista.

---

## 1. Contexto e problema

Hoje cada notícia recebe **uma única** categoria (`tipo_perigo`). Na prática, um
mesmo fato pode conter vários crimes: um roubo com emprego de arma é, ao mesmo
tempo, roubo e porte/uso de arma; uma morte durante assalto é latrocínio; uma
agressão sexual pode envolver violência física e ameaça.

Classificar em uma categoria só perde informação e distorce a priorização. Além
disso, não existe hoje nenhuma noção de **gravidade** derivada da lei: o app lê
`nivel_risco` (alto/médio/baixo), mas nada no repositório escreve essa coluna.

Este documento propõe:

1. uma taxonomia canônica com pena de referência por categoria;
2. um ranking das categorias pela média harmônica das penas;
3. categorias para crimes compostos (latrocínio, roubo armado);
4. o desenho multi-rótulo que será implementado nas fases seguintes.

---

## 2. Estado atual

| Camada | Situação |
|---|---|
| Banco | `danger_reports.tipo_perigo` é um `enum` de valor único (migration `0003_add_danger_report_types.sql`) |
| App | `nivel_risco` é lido no dashboard, mas nunca gravado |
| Prompt/LLM | saída com `tipo_perigo` string única (`scripts/data/eval/_eval_common.py`) |
| Scraper Facebook | `TIPO_PERIGO_VALUES` duplicado em `facebook_sjddoficial.py` |
| Populator | `REPORT_TYPES` duplicado em `danger-report-populator.py` |
| Flutter | três mapas de rótulo duplicados (`dashboard_screen`, `alerts_screen`, `admin_map_screen`) |

Há ainda divergência de identificadores entre as camadas:

- banco usa `area_deserta`; a avaliação usa `local_suspeito`;
- banco usa `incendio`; a avaliação usa `incendio_fumaca`.

A taxonomia canônica precisa resolver isso antes de qualquer migration.

---

## 3. Decisões de projeto

| Decisão | Escolha |
|---|---|
| Escopo desta rodada | taxonomia e ranking primeiro; banco, app e prompt depois |
| Métrica de gravidade | média harmônica de **todos** os enquadramentos da categoria |
| Formas penais incluídas | somente dolosas consumadas |
| Crimes duplos | conjunto amplo: latrocínio, roubo armado, homicídio, estupro, extorsão |
| Tráfico | categoria própria |
| Id canônico de “local suspeito” | `local_suspeito` (`area_deserta` vira alias) |
| Modelo multi-rótulo (fase futura) | array `tipos_perigo` + `tipo_perigo` principal |

---

## 4. Taxonomia proposta

São **18 categorias** (13 de crime e 5 sem pena), mais o sentinela `nenhum`.

### 4.1 Categorias de crime

Penas em meses. `H` é a média harmônica descrita na seção 5.

| Categoria | Enquadramentos | Pena (anos) | H (meses) |
|---|---|---|---:|
| `latrocinio` | CP 157 §3º II | 20–30 | **288,0** |
| `homicidio` | CP 121 caput; 121 §2º | 6–20; 12–30 | **144,0** |
| `estupro` | CP 213 caput/§1/§2; 217-A | 6–10; 8–12; 12–30; 8–15 | **106,7** |
| `extorsao` | CP 158; 159 caput/§1/§3 | 4–10; 8–15; 12–30; 24–30 | **103,8** |
| `roubo_arma` | CP 157 §2º I (+1/3 a 1/2) | 5a4m–15 | **94,4** |
| `trafico` | Lei 11.343/06 art. 33 | 5–15 | **90,0** |
| `assalto` | CP 157 caput | 4–10 | **68,6** |
| `incendio` | CP 250 | 3–6 | **48,0** |
| `presenca_arma` | Lei 10.826/03 arts. 14, 15, 16 | 2–4; 2–4; 3–6 | **36,0** |
| `furto` | CP 155 caput; §4º | 1–4; 2–8 | **25,6** |
| `assedio` | CP 216-A; 215-A | 1–2; 1–5 | **17,8** |
| `violencia_fisica` | CP 129 caput/§1/§2 | 3m–1a; 1–5; 2–8 | **10,5** |
| `perseguicao` | CP 147-A | 6m–2a | **9,6** |

> Os valores legais precisam de validação humana na fonte oficial antes de
> virarem código. Cada enquadramento no JSON exigirá `fonte_url`.

### 4.2 Categorias sem pena

| Categoria | Natureza | Motivo |
|---|---|---|
| `iluminacao_ruim` | infraestrutura | não é crime |
| `local_suspeito` | contexto | descreve o local, não o fato criminoso |
| `acidente_transito` | evento | fora do Código Penal (o CTB tem tipos próprios) |
| `via_bloqueada` | evento | não é crime |
| `emergencia_medica` | evento | não é crime |

Ficam fora do ranking, com `score: null`. O `nivel_risco` delas será decidido em
outra fase (faixas fixas ou regra própria).

### 4.3 Categorias novas

| Categoria | Por que entra |
|---|---|
| `latrocinio` | roubo seguido de morte não deve virar `assalto` + `violencia_fisica` |
| `roubo_arma` | roubo com arma é qualificado e hoje se perde como `assalto` |
| `homicidio` | morte violenta não pode continuar sendo só “violência física” |
| `estupro` | violência sexual tem tipo e pena próprios |
| `extorsao` | exigência de vantagem sob ameaça é crime autônomo |
| `trafico` | é recorrente no feed e hoje fica invisível em `local_suspeito` |

---

## 5. Método de cálculo

### 5.1 Fórmula

Para um enquadramento com pena mínima `a` e máxima `b`, em meses:

```
H_enquadramento = 2 · a · b / (a + b)
```

A categoria é a média harmônica dos `H` dos seus enquadramentos:

```
H_categoria = n / Σ (1 / H_i)
```

Como cada enquadramento contribui com exatamente dois valores (piso e teto),
isso equivale a calcular a média harmônica sobre todos os pisos e tetos da
categoria.

Ranking final: ordem decrescente de `H`.

### 5.2 Exemplos

**Latrocínio** (20–30 anos = 240–360 meses):

```
H = 2 · 240 · 360 / (240 + 360) = 172.800 / 600 = 288 meses
```

**Violência física**, com três enquadramentos:

| Enquadramento | Pena | H |
|---|---|---:|
| CP 129 caput (lesão leve) | 3–12 meses | 4,8 |
| CP 129 §1º (lesão grave) | 12–60 meses | 20,0 |
| CP 129 §2º (lesão gravíssima) | 24–96 meses | 38,4 |

```
H = 3 / (1/4,8 + 1/20 + 1/38,4) = 3 / 0,284375 = 10,5 meses
```

### 5.3 Critérios de inclusão

Entram no cálculo:

- formas **dolosas**;
- **consumadas**.

Ficam de fora:

- formas culposas (ex.: homicídio culposo, lesão culposa);
- formas privilegiadas;
- tentativa.

Motivo: a média harmônica é dominada pelo menor valor. Incluir o homicídio
culposo (1–3 anos) derrubaria o `homicidio` de 144 para aproximadamente 43
meses, colocando-o abaixo de `assalto` — o que não representa a gravidade da
categoria.

### 5.4 Limitações do método

- A média harmônica **puxa para baixo**: categorias com pena mínima baixa caem
  no ranking mesmo quando têm formas graves (é o caso de `violencia_fisica`).
- O ranking mede a pena **em abstrato**, não a gravidade do caso concreto.
- Categorias sem tipo penal não têm score; a ordem entre elas precisa de regra
  separada.
- O resultado depende da escolha dos enquadramentos; por isso cada um precisa
  de fonte e revisão.

---

## 6. Crimes duplos e precedência

As regras abaixo evitam dupla contagem: o composto substitui as componentes.
A ordem é de prioridade — a primeira que casar vence.

| # | Regra | Resultado | Remove |
|---|---|---|---|
| 1 | `assalto` + morte | `latrocinio` | `assalto`, `homicidio`, `violencia_fisica` |
| 2 | `assalto` + arma, sem morte | `roubo_arma` | `assalto`, `presenca_arma` |
| 3 | `violencia_fisica` + morte | `homicidio` | `violencia_fisica` |
| 4 | violência/assédio + conjunção carnal ou ato libidinoso | `estupro` | `violencia_fisica`, `assedio` |
| 5 | ameaça/violência + exigência de vantagem | `extorsao` | `assalto` (quando for extorsão) |

“Morte”, “arma” e “conjunção carnal” são **indicadores de evidência**, não
categorias. Na fase 3 o LLM passará a devolvê-los em um campo próprio, para que
as regras sejam aplicadas de forma determinística.

### Exemplos

- “Homem é assaltado e morto a tiros” → **`latrocinio`** (não `assalto` +
  `presenca_arma` + `homicidio`).
- “Assalto à mão armada em supermercado” → **`roubo_arma`**.
- “Mulher é agredida e morta pelo companheiro” → **`homicidio`** (e
  `violencia_fisica` não é repetida).
- “Ameaça funcionária e exige dinheiro do caixa” → **`extorsao`**.

---

## 7. Multi-rótulo (fases seguintes)

### 7.1 Banco de dados

Migration `0004`:

- adicionar ao enum: `homicidio`, `estupro`, `extorsao`, `latrocinio`,
  `roubo_arma`, `trafico`, `local_suspeito`;
- criar `tipos_perigo tipo_perigo_enum[] not null default '{}'`;
- backfill: `tipos_perigo = array[tipo_perigo]`;
- manter `tipo_perigo` como **principal** (maior `H`) para compatibilidade com
  filtros e telas atuais;
- índice GIN em `tipos_perigo`;
- calcular `nivel_risco` a partir do maior `H` do alerta.

### 7.2 Prompt e LLM

- trocar `tipo_perigo` por `tipos_perigo` (array, no máximo 3, ordenado por
  gravidade);
- adicionar `indicadores` (morte, arma, conjunção carnal, vantagem);
- aplicar as regras de precedência da seção 6;
- atualizar few-shot e scraper.

### 7.3 App

- centralizar rótulos e cores em um único helper (elimina os três mapas);
- exibir chips múltiplos nos cards;
- filtros por `contains` no array;
- decidir se o dashboard conta por rótulo ou apenas pelo principal;
- usar `nivel_risco` para a cor do marcador.

### 7.4 Avaliação

- reanotar os casos multi-crime do gabarito de 120 itens;
- manter `tipos_perigo[0]` para compatibilidade com as métricas atuais;
- acrescentar exact match, Hamming e P/R/F1 por rótulo;
- rodar novamente os três modelos com o prompt novo.

---

## 8. Plano por fases

| Fase | Entrega | Depende de |
|---|---|---|
| 1 | `taxonomy.json`, `build_ranking.py`, `RANKING.md`, documentação | — |
| 2 | prompt/scraper/eval multi-rótulo + reanotação | fase 1 |
| 3 | migration `0004`, backfill e `nivel_risco` | fase 1 |
| 4 | app: helper único, chips, filtros, dashboard | fase 3 |
| 5 | populator e futura ingestão usando array | fase 3 |

### Fase 1 — entregáveis

```
scripts/taxonomy/
  taxonomy.json        # fonte única: categorias, enquadramentos, penas, aliases, regras
  build_ranking.py     # valida, calcula H e gera o ranking
  RANKING.md           # gerado: ranking + auditoria por enquadramento
  TAXONOMIA.md         # método, critérios, compostos, pendências
```

Comportamento do script:

- valida ids únicos, `0 < min ≤ max`, `fonte_url`, referências de compostos e
  crime sem enquadramento;
- recusa categoria composta cujo `H` não supere o das componentes;
- gera `RANKING.md` ordenado por `H`, com tabela por enquadramento;
- `--check` falha se o arquivo gerado estiver defasado;
- `--json` imprime o ranking estruturado para consumo nas fases seguintes.

---

## 9. Critérios de aceite da fase 1

- [ ] 18 categorias, todas com `label`, `natureza` e `aliases`.
- [ ] Toda categoria de crime com ao menos um enquadramento e `fonte_url`.
- [ ] Ranking idêntico à seção 4.1, após validação jurídica.
- [ ] Compostos referenciando ids existentes e com `H` coerente.
- [ ] `build_ranking.py --check` verde.
- [ ] Nenhuma alteração fora de `scripts/taxonomy/`.

---

## 10. Pendências e riscos

1. **Validação jurídica** de todos os intervalos de pena na fonte oficial.
2. **Faixas de `nivel_risco`** ainda não definidas (sugestão: ≥120 meses alto,
   24–120 médio, <24 baixo; eventos sem pena precisam de regra própria).
3. **Divergência de ids**: `incendio` × `incendio_fumaca` e `local_suspeito` ×
   `area_deserta` serão resolvidas na migration.
4. **Acidentes de trânsito**: hoje ficam sem score; se entrar o CTB, a natureza
   passa a ser “evento com pena”.
5. **Tráfico**: inclui apenas o art. 33 caput; associação para o tráfico
   (art. 35) pode ser adicionada depois.
6. **Média harmônica** distorce categorias de pena mínima baixa; o documento
   registra isso explicitamente para não parecer erro de cálculo.

---

## 11. Referências legais

- Código Penal: arts. 121, 129, 147-A, 155, 157, 158, 159, 213, 215-A, 216-A,
  217-A, 250.
- Lei 10.826/2003: arts. 14, 15 e 16.
- Lei 11.343/2006: art. 33.
- Planalto: https://www.planalto.gov.br/ccivil_03/decreto-lei/del2848compilado.htm
