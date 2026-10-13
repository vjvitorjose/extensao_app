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

Para processar todas as noticias da entrada, uma por vez:

```powershell
.\.venv\Scripts\python.exe scripts\classificators\gemini-flash.py --all
```

Esse modo usa a API normal do Gemini e respeita o intervalo configurado entre
requisicoes. A cota gratuita e limitada e varia conforme modelo, projeto e
disponibilidade; o processamento das 1.311 noticias pode demorar bastante.
Erros temporarios de limite sao repetidos automaticamente. O processo pode
ser interrompido e retomado sem refazer as noticias ja salvas no checkpoint.
Os dados de entrada nao sao modificados.

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

Ao concluir `--all`, o resultado fica em
`data/classified/emboabas_gemini_3_1_flash_lite_all.json`. Os arquivos do
piloto e do lote completo contem `modelo`, `quantidade_noticias` e a lista
`alertas`.

## Retomada e checkpoint

No piloto, depois de cada noticia classificada, o script salva o resultado em:

```text
data/classified/emboabas_gemini_3_1_flash_lite_pilot5.checkpoint.json
```

No modo `--all`, as classificacoes sao salvas em
`data/classified/emboabas_gemini_3_1_flash_lite_all.checkpoint.json`. O
checkpoint e gravado atomicamente. A identidade de cada noticia e um hash
SHA-256 dos dados da noticia e do modelo. Ao executar novamente, o script:

1. valida o modelo e as classificacoes existentes no checkpoint;
2. reutiliza e pula noticias com hash correspondente;
3. classifica sequencialmente as noticias ainda pendentes;
4. atualiza o checkpoint depois de cada classificacao;
5. gera ou substitui o resultado final apenas quando todo o lote termina.

Se `Ctrl+C` interromper a classificacao, os resultados ja salvos permanecem no
checkpoint; execute novamente o mesmo comando para continuar.
Checkpoints invalidos ou incompativeis com o modelo causam erro explicito em
vez de serem descartados silenciosamente. Para recomecar intencionalmente,
remova somente o checkpoint correspondente em `data/classified/`.

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
progressivas para os demais erros temporarios. Erros permanentes e respostas
JSON invalidas encerram a execucao com erro explicito.
