# Classificadores

## Conteudo

No momento, esta pasta contem o classificador `gemini-flash.py`. Ele usa a API
REST do Google Gemini para transformar noticias de Sao Joao del-Rei em alertas
estruturados para o aplicativo.

## Requisitos e configuracao

- Python 3.10 ou superior.
- Nenhuma dependencia externa: o script usa a biblioteca padrao do Python.
- Uma chave da Gemini API com acesso ao modelo configurado.

Defina `GEMINI_API_KEY` no ambiente ou no arquivo `.env` na raiz do repositorio:

```env
GEMINI_API_KEY=sua-chave
```

O `.env` e ignorado pelo Git. Nao coloque a chave no codigo, nos logs ou em
commits. O script nao imprime a chave nem o texto integral das noticias.

## Execucao

Execute a partir da raiz do repositorio:

```powershell
.\.venv\Scripts\python.exe scripts\classificators\gemini-flash.py
```

O modo padrao e um piloto de 5 noticias, usando
`gemini-3.1-flash-lite` pela API `generateContent`. O limite esta definido em
`NEWS_LIMIT`. A troca de modelo e do nome dos arquivos preserva as avaliacoes
anteriores feitas com outros modelos.

Para processar todas as noticias da entrada pela Gemini Batch API:

```powershell
.\.venv\Scripts\python.exe scripts\classificators\gemini-flash.py --batch
```

O modo Batch divide as requisicoes em jobs de ate 100 noticias e submete os
jobs sem esperar respostas individuais. Em seguida, consulta o status a cada
30 segundos, coleta os resultados e atualiza o checkpoint noticia por noticia.
O processamento e assincrono e pode levar horas; a documentacao do Google
informa prazo-alvo de ate 24 horas para jobs Batch. O modo Batch usa todas as
noticias presentes na entrada, nao apenas as cinco do piloto. Se a entrada
ultrapassar os limites da API, o erro e reportado; os dados de entrada nao sao
modificados.

## Classificacao e arquivos gerados

O modelo escolhe exatamente um tipo de perigo:

- `assedio`
- `iluminacao_ruim`
- `perseguicao`
- `local_suspeito`
- `acidente_transito`
- `assalto`
- `furto`
- `violencia_fisica`
- `presenca_arma`
- `incendio_fumaca`
- `via_bloqueada`
- `emergencia_medica`
- `nenhum`

Cada alerta contem `tipo_perigo`, `descricao` curta e factual e `endereco` (ou
`null` quando nao ha local explicito). O resultado final tambem inclui titulo,
URL e data da noticia. Somente os campos esperados e tipos validos sao aceitos.

Ao concluir o piloto, o resultado final e escrito atomicamente em:

```text
data/classified/emboabas_gemini_3_1_flash_lite_pilot5.json
```

Ao concluir o modo Batch, o resultado fica em
`data/classified/emboabas_gemini_3_1_flash_lite_batch_all.json`. Ambos os
arquivos contem `modelo`, `quantidade_noticias` e a lista `alertas`.

## Retomada e checkpoint

No piloto, depois de cada noticia classificada, o script salva o resultado em:

```text
data/classified/emboabas_gemini_3_1_flash_lite_pilot5.checkpoint.json
```

No modo Batch, as classificacoes sao salvas em
`data/classified/emboabas_gemini_3_1_flash_lite_batch_all.checkpoint.json`, e os
nomes dos jobs e as noticias associadas ficam em
`data/classified/emboabas_gemini_3_1_flash_lite_batch_all.jobs.json`. Os arquivos
sao gravados atomicamente. A identidade de cada noticia e um hash SHA-256 dos
dados da noticia e do modelo. Ao executar novamente, o script:

1. valida o modelo e as classificacoes existentes no checkpoint;
2. reutiliza e pula noticias com hash correspondente;
3. no modo Batch, reutiliza os jobs submetidos que ainda nao foram coletados,
   sem reenviar essas noticias;
4. atualiza o checkpoint depois de cada classificacao coletada;
5. gera ou substitui o resultado final apenas quando todo o lote termina.

Se `Ctrl+C` interromper a classificacao, os resultados ja salvos permanecem no
checkpoint. No modo Batch, os jobs ja submetidos continuam no Google; execute
novamente o mesmo comando `--batch` para consultar os mesmos jobs e coletar os
resultados. Se um job terminar com falha, o script informa o estado e preserva
manifesto e checkpoint para diagnostico. Checkpoints/manifests invalidos ou
incompativeis com o lote atual causam erro explicito. Para recomecar
intencionalmente um lote Batch, remova apenas o manifesto e checkpoint Batch
correspondentes em `data/classified/`.

Os diretorios `data/raw/` e `data/classified/` sao ignorados pelo Git.

## Logs, limites e erros

Os logs incluem:

- inicio da execucao e modelo;
- quantidade de noticias carregadas e selecionadas;
- classificacoes reutilizadas do checkpoint e quantidade restante;
- inicio e duracao de cada tentativa de rede;
- resposta HTTP, numero da tentativa e espera antes de repetir;
- classificacao concluida e progresso persistido;
- caminho do resultado e duracao total.

No piloto, o script espera 4,1 segundos entre requisicoes novas, usa timeout
de 120 segundos por tentativa e faz ate quatro tentativas no total (uma inicial
e ate tres novas) em erros HTTP temporarios (429, 500, 502, 503 e 504) ou falhas
de comunicacao. Respeita `Retry-After` quando enviado pela API e usa esperas
progressivas para os demais erros temporarios. O modo Batch nao envia
requisicoes individuais: submete os jobs, registra os nomes antes de aguardar
e consulta seus estados a cada 30 segundos. Erros permanentes e respostas
JSON invalidas encerram a execucao com erro explicito.
