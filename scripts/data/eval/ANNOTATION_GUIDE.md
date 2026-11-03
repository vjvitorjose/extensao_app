# Guia de anotação — ground truth de alertas de segurança

Este documento descreve como o gabarito de 120 posts foi produzido. Ele serve para
(a) justificar as decisões de anotação, (b) permitir que outra pessoa revise o
gabarito e (c) deixar claro o que a avaliação dos LLMs mede e o que ela não mede.

## 1. Objetivo

Criar um ground truth manual, cego e reproduzível para comparar modelos de LLM na
classificação de notícias em tipos de perigo, no contexto de um aplicativo de
alertas de segurança de São João del-Rei.

Os pré-rótulos existentes em `facebook_sjddoficial_ai_reports.json` foram gerados
por um LLM e **não** foram usados como gabarito. Eles serviram apenas para
estratificar a amostra (garantir exemplos de classes raras e de baixa confiança).
Os anotadores não viram `tipo_perigo`, `confianca` ou `justificativa` do Gemini
durante a leitura dos itens.

## 2. Amostra

- **120 posts únicos** retirados de `facebook_sjddoficial_posts.json` (2.001 posts;
  1.765 únicos após deduplicação por título + conteúdo).
- Seed de amostragem: **20261102**.
- Amostra estratificada, não aleatória simples. A composição inclui:
  - todas as classes raras disponíveis no pool pré-classificado
    (`assedio`, `perseguicao`, `assalto`, `emergencia_medica`);
  - amostras de classes frequentes (`furto`, `incendio`, `presenca_arma`,
    `violencia_fisica`, `acidente_transito`);
  - 20 itens que o Gemini havia marcado como `nenhum`;
  - 30 posts fora do pool pré-classificado que continham termos de perigo mais
    amplos (possíveis falsos negativos do filtro lexical);
  - 30 posts fora do pool, aleatórios.
- A ordem final foi embaralhada. O arquivo `annotation_blind.jsonl` contém apenas
  `id`, `fonte_url`, `fonte_data`, `titulo`, `conteudo_completo` e campos de
  anotação vazios.
- **A amostra não representa a prevalência real do feed.** As classes raras foram
  superamostradas de propósito. Por isso, não use a proporção de `nenhum` deste
  gabarito para estimar a proporção de `nenhum` no feed inteiro.

## 3. Área de cobertura

A página cobre “São João del-Rei e outras cidades da região”. Para o aplicativo,
a área de cobertura adotada foi:

- **Incluída:** município de São João del-Rei e municípios do Campo das Vertentes
  que aparecem com frequência na página, como Barbacena, Tiradentes, Resende
  Costa, Lagoa Dourada, Dores de Campos, Santa Cruz de Minas e Prados. A Serra de
  São José, por ficar entre São João del-Rei, Tiradentes e Santa Cruz de Minas,
  também foi considerada área de cobertura.
- **Excluída:** Belo Horizonte e região metropolitana, Zona da Mata (Juiz de Fora,
  Ubá), Sul de Minas (Varginha), Rio de Janeiro, Brasília, Campinas, Recife e
  outros estados/países.

A geografia **não muda o tipo do evento**. Uma notícia fora da área que descreve
um incêndio continua sendo `incendio_fumaca`; o que muda é a relevância para o
produto. Nesses casos, o item recebe o tipo do evento, `fora_da_area = true` e
`relevante = false`. A justificativa é de produto: um alerta de incêndio em Belo
Horizonte ou de assalto em Ubá não é acionável para o morador de São João
del-Rei e aumentaria o ruído do aplicativo.

Exemplo: `sjd-012` é um ônibus incendiado em Venda Nova, Belo Horizonte. O tipo
é `incendio_fumaca` (o evento aconteceu), mas o item não é alertável
(`relevante = false`, `fora_da_area = true`). Já notícias fora da área que não
descrevem nenhum evento de perigo — obituário, campanha, cartaz de procurado —
continuam como `nenhum`.

Casos de fronteira (por exemplo, uma ocorrência em Tiradentes ou Barbacena) foram
incluídos porque a página os trata como notícia regional e porque o deslocamento
entre essas cidades é parte do cotidiano local. Se o produto decidir restringir a
cobertura ao município de São João del-Rei, esses itens precisam ser reanotados;
o campo `endereco` permite filtrar por município.

## 4. Regra de relevância

A anotação separa duas decisões:

1. **Tipo do evento** (`tipo_perigo`): qual é o fato descrito, mesmo que ele tenha
   ocorrido fora da área. Se não houver evento de perigo, o tipo é `nenhum`.
2. **Relevância para o alerta** (`relevante`): o item é acionável para o morador
   de São João del-Rei. Só é `true` quando o tipo não é `nenhum` **e** o evento
   ocorreu na área de cobertura.

Um item é **alertável** quando atende, ao mesmo tempo, aos critérios abaixo:

1. **Fato:** a notícia descreve um evento concreto, não opinião, campanha,
   projeto, previsão, boato ou conteúdo institucional.
2. **Atualidade:** o evento é recente ou está em curso. Eventos históricos,
   retrospectivas e desdobramentos administrativos de casos antigos não contam.
3. **Tipo:** o evento se encaixa em um dos tipos de perigo da taxonomia.
4. **Área e acionabilidade:** o evento ocorreu na área de cobertura definida na
   seção 3 e um morador pode ser alertado, ainda que o endereço seja apenas o
   município ou o bairro.

Foram considerados **não alertáveis** (`relevante = false`):

- cultura, religião, esporte, política, administração pública, obras, serviços,
  campanhas, eventos e entretenimento;
- previsão do tempo, obituário, história, curiosidade, meme e opinião;
- boato desmentido pela polícia;
- ação policial já concluída, sem risco atual identificável (por exemplo, prisão
  de suspeito após denúncia, drogas apreendidas em hospital);
- crime que não se encaixa em nenhum tipo da taxonomia (racismo, erro médico,
  alerta genérico de saúde pública);
- interdição de via **planejada** para obra, evento ou procissão;
- notícia fora da área de cobertura: recebe `fora_da_area = true`, mas mantém o
  tipo do evento se houver um.

Itens ambíguos não foram descartados: receberam o tipo mais provável, confiança
baixa e `revisar = true`.

## 5. Taxonomia

A taxonomia é a do branch `feature/llm-classification`, com a unificação
`incendio` → `incendio_fumaca` e string vazia → `nenhum`.

| Tipo | Definição operacional | Exemplos no gabarito | N |
|---|---|---|---|
| `assedio` | Assédio ou importunação, inclusive sexual, contra uma pessoa. | 003, 022 | 2 |
| `iluminacao_ruim` | Local com iluminação pública insuficiente, relatado como risco. | nenhum exemplo na amostra | 0 |
| `perseguicao` | Pessoa sendo seguida/perseguida ou perseguição policial com risco viário. | 028, 090, 117 | 3 |
| `local_suspeito` | Ponto de tráfico, estabelecimento ou local com atividade suspeita e risco sanitário/segurança. | 043, 051, 064 | 3 |
| `acidente_transito` | Colisão, batida, atropelamento, capotamento ou acidente envolvendo veículo. | 010, 018, 026, 101 | 4 |
| `assalto` | Roubo com ameaça ou força, inclusive com arma branca ou de fogo. | 014, 047, 089, 110, 111, 114 | 6 |
| `furto` | Subtração sem ameaça ou violência contra a pessoa. | 030, 041, 056, 071 | 4 |
| `violencia_fisica` | Agressão física, briga, violência doméstica, homicídio/feminicídio por meio diverso de arma de fogo. | 002, 031, 042, 066, 073, 079, 113 | 7 |
| `presenca_arma` | Disparos, pessoa baleada, arma portada/apreendida ou ameaça com arma de fogo. | 006, 007, 037, 048, 112 | 5 |
| `incendio_fumaca` | Incêndio ou fumaça ativo/recente, inclusive desdobramentos próximos. | 012, 036, 040, 076, 091, 102 | 6 |
| `via_bloqueada` | Via bloqueada ou alagada por um incidente não planejado. | 034, 046, 118 | 3 |
| `emergencia_medica` | Emergência médica, mal súbito, afogamento, acidente com ferido, ataque de animais, resgate ou morte acidental. | 004, 015, 024, 027, 029, 038, 054, 060, 063, 096, 120 | 11 |
| `nenhum` | Não há evento de segurança relevante para alertar. | 66 itens | 66 |

**Total:** 120 itens; 54 com tipo de evento; **53 alertáveis** e 67 não alertáveis
(66 `nenhum` + `sjd-012`, que é `incendio_fumaca` fora da área).

## 6. Regras de desempate

Como cada item recebe **um único** tipo principal, estas regras foram aplicadas:

- **`assalto` vs `presenca_arma`:** se o evento central é um roubo consumado,
  mesmo com arma, vale `assalto` (014, 047, 110, 114). Se o evento central é
  disparo, pessoa baleada ou arma portada sem roubo, vale `presenca_arma`
  (006, 007, 037, 048, 112).
- **`violencia_fisica` vs `presenca_arma`:** arma de fogo → `presenca_arma`;
  agressão, briga, faca, violência doméstica ou homicídio por outro meio →
  `violencia_fisica` (079, 113).
- **`perseguicao` vs `presenca_arma`:** quando a perseguição é o evento central,
  vale `perseguicao` (028, 090, 117), ainda que haja arma envolvida.
- **`incendio_fumaca` vs `emergencia_medica`:** quando o fogo é o evento central,
  vale `incendio_fumaca`; quando o evento central é o ferimento ou resgate sem
  fogo, vale `emergencia_medica`.
- **`via_bloqueada` vs `acidente_transito`:** acidente com via bloqueada →
  `acidente_transito`; alagamento ou veículo preso sem colisão → `via_bloqueada`.
- **`local_suspeito` vs `nenhum`:** ponto de tráfico ou estabelecimento suspeito
  com local identificável → `local_suspeito`; ação policial genérica, sem local e
  já concluída → `nenhum` (064 ficou como `local_suspeito` com baixa confiança
  justamente porque o local não foi especificado).
- **Interdição planejada → `nenhum`:** procissões, obras e montagem de estruturas
  não são tratadas como `via_bloqueada` (050, 092).
- **`assedio` vs `violencia_fisica`:** crimes sexuais, importunação e assédio
  contra uma pessoa → `assedio` (003, 022); agressão física, briga, violência
  doméstica e homicídio → `violencia_fisica` (002, 031, 042, 066, 073, 079, 113).
- **Fora da área:** a geografia não altera o tipo. O item recebe o tipo do evento
  e é marcado com `fora_da_area = true` e `relevante = false` (012). Se não há
  evento de perigo, permanece `nenhum` (055, 075, 077, 082, 083).

## 7. Confiança e revisão

- `confianca >= 0.90`: alta. Evento explícito, tipo claro, local explícito ou
  consequência inequívoca.
- `0.70 <= confianca < 0.90`: média. Texto truncado, título claro mas detalhes
  ausentes, ou tipo com pequena ambiguidade.
- `confianca < 0.70`: baixa. Circunstâncias desconhecidas, local não confirmado,
  tipo debatível ou informação insuficiente. Nesses casos, `revisar = true`.

**14 itens marcados para revisão:**

| ID | Tipo | Confiança | Motivo |
|---|---|---|---|
| sjd-015 | `emergencia_medica` | 0.65 | Texto truncado; extensão do atendimento não confirmada. |
| sjd-022 | `assedio` | 0.65 | Texto truncado; tipo inferido do título (“importunação”). |
| sjd-031 | `violencia_fisica` | 0.70 | Operação policial com resistência; tipo debatível. |
| sjd-042 | `violencia_fisica` | 0.55 | Mulher encontrada morta; causas desconhecidas. |
| sjd-046 | `via_bloqueada` | 0.60 | Carro preso em beco; bloqueio pontual e já resolvido. |
| sjd-051 | `local_suspeito` | 0.65 | Risco sanitário (bebida falsificada); tipo debatível. |
| sjd-054 | `emergencia_medica` | 0.50 | Texto truncado; cidade do desabamento não confirmada. |
| sjd-064 | `local_suspeito` | 0.55 | Tráfico; local não especificado e ação concluída. |
| sjd-073 | `violencia_fisica` | 0.50 | Corpo no rio; circunstâncias da morte desconhecidas. |
| sjd-084 | `nenhum` | 0.60 | Fogos de artifício; sem feridos/incêndio confirmados. |
| sjd-098 | `nenhum` | 0.70 | Morte após procedimento odontológico; caso investigado. |
| sjd-101 | `acidente_transito` | 0.65 | Texto truncado; cidade inferida. |
| sjd-107 | `nenhum` | 0.70 | Alerta de dengue sem local ou evento específico. |
| sjd-109 | `nenhum` | 0.65 | Feto encontrado em ETE; circunstâncias desconhecidas. |

## 8. Limitações

1. **Textos truncados:** 20 dos 120 itens têm apenas o teaser do Facebook
   (terminam em “Ver mais”), e 16 deles são relevantes. Em vários casos o tipo foi
   decidido pelo título. Isso afeta principalmente 015, 022, 029, 038, 054, 066,
   084, 089, 090, 096, 101, 111, 117 e 118.
2. **Datas ausentes:** 24 itens não têm `fonte_data`; a atualidade foi julgada
   pelo texto (“nesta terça-feira”, “nesta madrugada” etc.).
3. **Amostra estratificada:** não serve para estimar prevalência. Serve para
   comparar modelos nos mesmos itens, com cobertura razoável de classes raras.
4. **Uma única anotadora/pessoa anotadora:** não há medida de concordância entre
   anotadores. Os 14 itens com `revisar = true` são os candidatos naturais para
   uma segunda opinião.
5. **Classe sem suporte:** `iluminacao_ruim` não tem nenhum exemplo na amostra.
   Qualquer métrica por classe para ela ficará indefinida; reporte isso.
6. **Lacunas da taxonomia:** racismo, erro médico, alerta genérico de saúde
   pública, maus-tratos a animais e mortes por causa desconhecida não têm tipo
   próprio. Nesses casos, a decisão foi `nenhum` ou o tipo mais próximo, com
   observação.
7. **Endereço:** foi extraído apenas quando explícito no texto. Não houve
   geocodificação nem inferência de coordenadas. Em 101, a cidade foi inferida
   pelo contexto da página e o item está marcado para revisão.
8. **Pré-rótulos do Gemini:** não foram usados como gabarito e não devem ser
   tratados como verdade. A taxonomia antiga usa `incendio` e string vazia para
   “não relevante”; para comparar, mapeie `incendio` → `incendio_fumaca` e
   vazio → `nenhum`.

## 9. Arquivos

| Arquivo | Conteúdo |
|---|---|
| `annotation_blind.jsonl` | 120 itens cegos, com campos de anotação vazios. |
| `ground_truth.jsonl` | 120 itens com o gabarito completo. |
| `ground_truth.csv` | Mesmo conteúdo em CSV (UTF-8 com BOM, para abrir no Excel). |
| `sample_manifest.json` | Seed, universo e estrato de cada item. **Não use os estratos para anotar**, pois eles revelam o pré-rótulo do Gemini. |
| `_build_ground_truth.py` | Script que consolida as anotações e valida IDs, tipos e confiança. |
| `ANNOTATION_GUIDE.md` | Este guia. |

Campos do gabarito: `id`, `fonte_url`, `fonte_data`, `titulo`,
`conteudo_completo`, `tipo_perigo`, `descricao`, `endereco`, `confianca`,
`revisar`, `observacoes`, `fora_da_area`, `relevante`.

`fora_da_area` e `relevante` são derivados no script: `fora_da_area` é `true`
quando `observacoes` contém a marca `fora_da_area`; `relevante` é
`tipo_perigo != "nenhum"` **e** `fora_da_area == false`. Use `relevante` para a
métrica binária e `tipo_perigo` para a métrica multiclasse.

## 10. Como usar na avaliação

1. Carregue `ground_truth.jsonl`.
2. Use `relevante` para a avaliação binária (alerta sim/não) e `tipo_perigo`
   para a avaliação multiclasse. Um item fora da área com tipo de evento
   (`sjd-012`) é `relevante = false`; se o modelo alertar para ele, conte como
   falso positivo.
3. Rode os modelos no mesmo conjunto de 120 itens, com o mesmo prompt few-shot,
   a mesma taxonomia e temperatura 0 (ou a menor disponível).
4. Normalize a saída do modelo para a taxonomia unificada antes de comparar.
5. Reporte, no mínimo:
   - macro-F1 multiclasse (classes com suporte ≥ 1; informe que
     `iluminacao_ruim` tem suporte 0);
   - precisão, recall e F1 por classe, com o suporte;
   - matriz de confusão;
   - acurácia binária de `relevante` (não use `tipo_perigo != nenhum`);
   - taxa de JSON inválido ou fora do schema;
   - acerto de endereço (comparação textual normalizada, não geocodificada);
   - latência e custo por item.
6. Avalie a área separadamente: quantos itens fora da área o modelo marcou como
   alertáveis. O gabarito tem 6 itens com `fora_da_area = true`, sendo 1 com
   tipo de evento (`sjd-012`).
7. Separe os exemplos de few-shot **fora** destes 120 itens. Não use itens do
   gabarito como exemplo no prompt, para não vazar a resposta.
8. Não compare diretamente com os 478 pré-rótulos antigos como se fossem
   ground truth. Se quiser usar o Gemini antigo como baseline, trate-o como mais
   um modelo e explicite a diferença de prompt/taxonomia.
