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
