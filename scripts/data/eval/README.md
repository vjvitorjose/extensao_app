# Avaliação dos classificadores de alertas

Compara LLMs na mesma amostra cega de 120 posts, com o mesmo prompt few-shot e
o mesmo gabarito anotado manualmente.

## Arquivos principais

| Arquivo | Papel |
|---|---|
| `annotation_blind.jsonl` | 120 posts sem pré-rótulo, usados na avaliação |
| `ground_truth.jsonl` / `.csv` | Gabarito anotado manualmente |
| `few_shot_examples.jsonl` | 26 exemplos completos, 2 por classe |
| `few_shot_examples_compact.jsonl` | Mesmos exemplos com conteúdo truncado em 600 caracteres; usado pelo modelo local |
| `sample_manifest.json` | Seed, estratos e composição da amostra |
| `_eval_common.py` | Prompt, parsing tolerante e normalização |
| `run_eval.py` | Executa um modelo e grava JSONL incremental |
| `evaluate.py` | Métricas, matriz de confusão, bootstrap e comparação pareada |
| `runs/` | Respostas brutas por modelo |
| `reports/` | Relatórios `.md` e `.json` |

Os três runs principais (`deepseek_flash_compact`, `gemini_3_1_flash_lite_compact`
e `ollama_qwen3_8b_compact`, com `.jsonl`, `.meta.json` e `.summary.json`) são
versionados. Arquivos com prefixo `_` (probes/smoke) e o restante de
`scripts/data/` continuam fora do Git.

## Provedores

```powershell
# Modelo local gratuito (Ollama), uma sessão por item
python scripts/data/eval/run_eval.py --model ollama/qwen3:8b `
  --few-shot scripts/data/eval/few_shot_examples_compact.jsonl `
  --run-name ollama_qwen3_8b_compact

# Gemini
python scripts/data/eval/run_eval.py --model gemini/gemini-3.1-flash-lite `
  --few-shot scripts/data/eval/few_shot_examples_compact.jsonl `
  --run-name gemini_3_1_flash_lite_compact

# DeepSeek pago via OpenCode
python scripts/data/eval/run_eval.py --model deepseek/deepseek-flash `
  --few-shot scripts/data/eval/few_shot_examples_compact.jsonl `
  --run-name deepseek_flash_compact

# Modelos free do OpenCode (big-pickle e DeepSeek free)
python scripts/data/eval/run_eval.py --model opencode/big-pickle
```

O runner retoma automaticamente: itens já concluídos no JSONL não são refeitos.
Use `--ids sjd-001,sjd-002` para refazer itens específicos e `--dry-run` para
ver o tamanho do prompt.

## Limites observados

- **OpenCode free:** o limite é por sessão. A primeira geração de cada sessão
  passa; a segunda recebe HTTP 503 `Free usage limit reached`. O runner cria uma
  sessão nova por item e apaga em seguida. Além disso, há um limite global por
  período (observado perto de 50 gerações), que pode interromper uma execução
  longa.
- **Gemini 3.8 Flash:** indisponível por alta demanda (HTTP 503) em 03/11/2026.
  `gemini-3.1-flash-lite` respondeu normalmente.
- **DeepSeek pago:** pode retornar `Insufficient Balance`; o runner registra o
  erro e permite refazer os IDs depois.
- **Ollama:** o modelo roda 100% na GPU (RX 6700 XT, ROCm) e leva ~17 s/item
  depois do carregamento inicial.

## Métricas

O relatório inclui:

- acurácia e macro-F1 multiclasse (classes com suporte ≥ 1; `iluminacao_ruim`
  tem suporte 0);
- precisão, recall, F1, suporte e nº previsto por classe;
- matriz de confusão;
- acurácia, precisão, recall e F1 binários de `relevante`;
- tratamento de área: itens fora da área que o modelo alertou;
- JSON inválido e fora do schema;
- acerto textual de endereço (exato, contém, fuzzy);
- latência média/mediana/p95 e custo reportado;
- IC 95% por bootstrap;
- comparação pareada nos itens respondidos por todos os modelos.

## Comandos de avaliação

```powershell
# Um run
python scripts/data/eval/evaluate.py `
  scripts/data/eval/runs/deepseek_flash_compact.jsonl `
  --out-dir scripts/data/eval/reports --name deepseek_compact

# Comparação de todos os runs (ignora arquivos que começam com "_")
python scripts/data/eval/evaluate.py `
  --out-dir scripts/data/eval/reports --name comparison --bootstrap 1000
```

O CSV do gabarito serve para revisão humana; o JSONL é a fonte de verdade.

## Estudo multi-fonte e multi-rótulo

`multilabel_study.py` prepara um estudo separado da avaliação histórica acima.
Se você já tem a amostra aleatória de 90 notícias, importe-a diretamente: o
pipeline não coleta, filtra nem reamostra esses itens. Aceita JSON (lista),
JSONL ou CSV com título e conteúdo.

```powershell
# Importa a lista existente de 90 notícias e gera fichas cegas para os três avaliadores
python scripts/data/eval/multilabel_study.py import-sample --input caminho\para\amostra.jsonl

# Alternativa apenas se ainda não houver uma amostra pronta:
# coleta os arquivos locais, filtra regex e sorteia itens entre fontes
python scripts/data/eval/multilabel_study.py prepare --count 30 --seed 20261124

# Para executar sobre toda a base local dos scrapers (sem amostragem):
python scripts/data/eval/multilabel_study.py prepare-full

# Cada anotador preenche seu próprio CSV sem consultar os demais nem os modelos.
# tipos_perigo e indicadores são códigos separados por ponto e vírgula.
# Para nenhuma classe de perigo, preencha tipos_perigo com "nenhum".
# fora_da_area e relevante devem ser true/false.

# Depois de preencher os três CSVs, cria a maioria provisória e relatório de divergências
python scripts/data/eval/multilabel_study.py consensus `
  --annotations scripts/data/eval/study_multilabel/annotator_1.csv `
  --annotations scripts/data/eval/study_multilabel/annotator_2.csv `
  --annotations scripts/data/eval/study_multilabel/annotator_3.csv

# Executar nos 90 itens anotados ou, para a base completa, passar full_corpus.jsonl.
# Os modelos recebem o mesmo prompt e os mesmos exemplos few-shot sintéticos.
python scripts/data/eval/multilabel_study.py run
python scripts/data/eval/multilabel_study.py run `
  --input scripts/data/eval/study_multilabel/full_corpus.jsonl `
  --out-dir scripts/data/eval/study_multilabel/full_corpus_runs

# Calcular métricas após as anotações humanas e execuções dos modelos
python scripts/data/eval/multilabel_study.py evaluate `
  scripts/data/eval/study_multilabel/runs/deepseek_deepseek-flash.jsonl `
  scripts/data/eval/study_multilabel/runs/gemini_gemini-3.1-flash-lite.jsonl `
  scripts/data/eval/study_multilabel/runs/ollama_qwen3_8b.jsonl
```

O prompt usa **few-shot** com 21 exemplos sintéticos versionados em
`few_shot_multilabel.jsonl`: há um exemplo para cada uma das 19 classes
(incluindo `nenhum`), um exemplo adicional de evento fora da área e um exemplo
com múltiplos rótulos. Eles não foram retirados da amostra nem do gabarito,
evitando vazamento direto dos itens avaliados. Os três modelos recebem
exatamente os mesmos exemplos. Para uma comparação zero-shot opcional, passe
`--few-shot ""` ao comando `run`.

O carregador lê `scripts/.env` e também `.env` na raiz do repositório, sem
imprimir os valores das variáveis. Se a mesma variável estiver nos dois, o
valor em `scripts/.env` tem precedência. O runner pausa um modelo quando a
cota diária acaba, ocorre erro não repetível ou aparecem três erros de
provedor seguidos; as notícias restantes permanecem pendentes para retomar
depois.

A saída pede no máximo três rótulos, categoria principal, indicadores
de evidência, relevância geográfica e confiança. O relatório calcula exact
match, Hamming loss, F1 micro/macro e por classe, métricas binárias de
relevância/área, validade do JSON, latência e custo. Rótulos sem exemplos no
ground truth aparecem com suporte zero; não entram no macro-F1 de classes
suportadas. O relatório de consenso também mostra concordância exata entre
conjuntos de rótulos e Cohen kappa por rótulo, além dos itens/campos divergentes.

### Protocolo humano e taxonomia

Os três anotadores recebem as mesmas notícias sem pré-rótulos. Devem preencher
`tipos_perigo` com até três códigos, ordenados da maior gravidade para a menor,
e marcar `nenhum` sozinho quando não houver evento da taxonomia. A maioria é
calculada por rótulo; divergências são destacadas para revisão. `relevante` só
deve ser true quando houver um evento da taxonomia dentro da área de cobertura;
no consenso final esse campo é derivado dos rótulos e da votação de área, para
evitar combinações contraditórias.
Uma ocorrência fora da área mantém seus rótulos, mas recebe `fora_da_area=true`
e `relevante=false`.

| Código | Critério operacional resumido |
|---|---|
| `latrocinio` | Roubo seguido de morte; substitui os rótulos componentes. |
| `homicidio` | Morte violenta intencional, exceto latrocínio. |
| `estupro` | Estupro ou violência sexual com conjunção carnal/ato libidinoso. |
| `extorsao` | Exigência de vantagem mediante ameaça ou violência. |
| `roubo_arma` | Roubo consumado com arma de fogo; substitui assalto e presença de arma. |
| `trafico` | Comércio ou distribuição de drogas descrito como tráfico. |
| `assalto` | Roubo consumado mediante ameaça ou força, exceto compostos acima. |
| `incendio` | Incêndio ou fumaça ativo/recente. |
| `presenca_arma` | Disparo, pessoa baleada, arma de fogo portada/apreendida ou ameaça com arma, sem roubo armado. |
| `furto` | Subtração sem ameaça ou violência contra a pessoa. |
| `assedio` | Assédio ou importunação, inclusive sexual, sem elementos para estupro. |
| `violencia_fisica` | Agressão, briga ou violência doméstica, exceto morte/estupro já classificados. |
| `perseguicao` | Pessoa seguida/perseguida ou perseguição policial com risco viário. |
| `iluminacao_ruim` | Iluminação pública insuficiente, relatada como risco. |
| `local_suspeito` | Local identificável com atividade suspeita e risco de segurança ou sanitário. |
| `acidente_transito` | Colisão, batida, atropelamento, capotamento ou acidente com veículo. |
| `via_bloqueada` | Via bloqueada/alagada por incidente não planejado, sem acidente de trânsito. |
| `emergencia_medica` | Emergência médica, mal súbito, afogamento, acidente com ferido, ataque animal, resgate ou morte acidental. |
| `nenhum` | Nenhum evento de perigo desta taxonomia. |

Indicadores são códigos de evidência, não rótulos: `morte`, `arma`,
`ato_sexual`, `vantagem`. Use somente o que estiver apoiado pelo texto. Para
casos compostos, siga as precedências acima e as instruções mais detalhadas do
prompt versionado no script.

`import-sample` exige exatamente 90 registros por padrão; use `--count` se a
amostra tiver outro tamanho. Preserva IDs existentes ou cria IDs estáveis,
recusa IDs repetidos e falha sem alterar a seleção se a contagem diferir. As
três fichas contêm a mesma amostra, para cada avaliador classificar cada item
independentemente.

As fichas, notícias, respostas brutas e relatórios ficam em
`scripts/data/eval/study_multilabel/`, ignorado pelo Git por conter conteúdo de
terceiros. O arquivo `manifest.json` registra a origem e contagem por fonte.
Revise o relatório de divergências antes de considerar a maioria dos três
anotadores como ground truth definitivo. Trinta itens e uma amostra balanceada
entre fontes são exploratórios: não estimam prevalência nem desempenho em
produção, e classes raras podem não aparecer.

Os runs históricos nesta pasta continuam usando a taxonomia anterior de rótulo
único; não os misture com os resultados do estudo multi-rótulo.
