# Scrapers

Este diretorio (`scripts/scrapers/`) possui quatro scripts Python independentes
para coletar dados reais de fontes publicas. Emboabas e G1 geram arquivos JSON; a
SEJUSP gera arquivos CSV filtrados para Sao Joao del-Rei; o scraper do Facebook
gera JSON a partir de uma pagina publica e classifica o conteudo por LLM.

Os dados coletados ficam em `scripts/data/` (pasta ignorada pelo Git, pois
contem conteudo de terceiros).

## Pre-requisitos

- Python 3.10 ou superior.
- Conexao com a internet no momento da execucao.
- Emboabas, G1 e SEJUSP **nao tem dependencias externas**: usam apenas a stdlib.
- O scraper do Facebook precisa de um ambiente virtual proprio, porque usa
  Playwright e a API do Gemini. Ver a secao dele abaixo.

## Execucao

Execute da raiz do projeto. Rode os scrapers que desejar; nenhum depende dos
outros:

```powershell
py scripts\scrapers\emboabas.py
py scripts\scrapers\g1_sao_joao_del_rei.py
py scripts\scrapers\sejusp.py
```

Os populators sao rotinas separadas; consulte `scripts/populators/POPULATOR.md`
para instrucoes proprias.

## Scrapers disponíveis

### emboabas.py

**Fonte:** https://emboabas.com — Radio Emboabas, Sao Joao del-Rei, MG

**Metodo:** WordPress REST API (`/wp-json/wp/v2/posts`). Nenhuma dependencia
externa necessaria, apenas `urllib` da stdlib.

**Categorias coletadas:**

| ID | Categoria  | Total disponivel |
|----|------------|-----------------|
| 66 | Policial   | ~591 posts       |
| 10 | Cidade     | ~729 posts       |

**Saida:** `scripts/data/emboabas_danger_reports.json`

Cada entrada do JSON possui os campos:

| Campo               | Descricao                                                      |
|---------------------|----------------------------------------------------------------|
| `titulo`            | Titulo do artigo                                               |
| `descricao`         | Primeiras 2-3 frases; pronto para uso imediato no populador    |
| `conteudo_completo` | Texto integral do artigo (para classificacao via LLM)          |
| `endereco`          | Bairro/rua extraido por regex do conteudo (pode ser `null`)    |
| `fonte_url`         | URL do artigo original                                         |
| `fonte_data`        | Data de publicacao (ISO 8601)                                  |

> O campo `tipo_perigo` **nao e gerado por este scraper**. A classificacao
> por LLM existe apenas em `facebook_sjddoficial.py`, que a faz para os proprios
> posts. Emboabas e G1 continuam produzindo texto sem `tipo_perigo`.
>
> Este arquivo **nao e lido por nenhum script**. Os populators geram dados
> ficticios do zero; ver `scripts/populators/POPULATOR.md`.

**Execucao:**

```powershell
py scripts\scrapers\emboabas.py
```

**Rate limiting:** pausa de 0,5 s entre paginas; respostas HTTP 429 sao
repetidas ate 3 vezes respeitando o header `Retry-After`.

### g1_sao_joao_del_rei.py

**Fonte:** https://g1.globo.com/mg/zona-da-mata/ — G1 Zona da Mata

**Metodo:** Leitura do RSS Feed Oficial nativo do G1, com filtragem local por texto. Nenhuma dependencia externa necessaria.

**Categorias coletadas:** Feed de Noticias de toda a Zona da Mata e Campo das Vertentes. O script filtra automaticamente os itens que mencionam "São João del Rei" no título ou descrição.

**Saida:** `scripts/data/g1_sao_joao_del_rei_reports.json`

O JSON gerado segue exatamente o mesmo padrão do `emboabas.py`.

**Execucao:**

```powershell
py scripts\scrapers\g1_sao_joao_del_rei.py
```

### sejusp.py

**Fonte:** [Portal de Dados Abertos de Minas Gerais](https://www.dados.mg.gov.br/),
plataforma CKAN utilizada pela SEJUSP-MG.

**Metodo:** consulta a API CKAN (`resource_show`) para obter os metadados e a URL
oficial dos recursos definidos na lista `RESOURCE_URLS` dentro do script; em
seguida, baixa cada CSV e mantém somente registros de São João del-Rei. Nao
requer dependencias externas.

```powershell
py scripts\scrapers\sejusp.py
```

O script esta configurado com 12 recursos: Crimes Violentos, Feminicidio,
Violencia Domestica e Vitimas de Acidentes de Transito, cada um para 2024, 2025
e 2026. Recursos que nao sejam identificados como CSV sao recusados.

**Saida:** cada CSV filtrado e salvo diretamente em `scripts/data/<arquivo>.csv`;
nenhum arquivo lateral de metadados ou subpasta SEJUSP e criado. Os nomes dos
arquivos distinguem conjunto e ano. O filtro usa o código IBGE `316250` nas
colunas municipais próprias de cada conjunto. Cabeçalho, colunas e delimitador
`;` são mantidos. A quantidade de linhas baixadas e mantidas aparece no
terminal. Se um recurso não tiver registros da cidade, o CSV conterá apenas o
cabeçalho. Os arquivos não são convertidos ao esquema de notícias/alertas usado
por Emboabas e G1.

**Referencias:** [conjunto Crimes Violentos](https://www.dados.mg.gov.br/dataset/crimes-violentos)
e [documentacao da API CKAN](https://docs.ckan.org/en/2.10/api/).

### facebook_sjddoficial.py

**Fonte:** https://www.facebook.com/sjddoficial — pagina oficial do municipio.

**Por que este scraper e diferente dos outros tres:** o Facebook nao oferece API
publica para leitura de paginas de terceiros. A Graph API exige app review para
`pages_read_engagement`, o RSS publico foi removido em 2019 e os conectores do
IFTTT/Zapier foram descontinuados. E ele o unico dos quatro que **precisa de
autenticacao**: a pagina so renderiza posts para um navegador logado.

Por isso ele usa Playwright com um perfil de navegador persistente, e a
classificacao por LLM (Gemini) decide o que vira alerta. A extracao e ancorada
em elementos estruturais (`role="article"` e hrefs `*/posts/*`), nunca em classe
CSS: as classes do Facebook sao ofuscadas e rotacionam com frequencia.

**Instalacao (uma vez):**

```powershell
python -m venv scripts\.venv
scripts\.venv\Scripts\python -m pip install -r scripts\scrapers\requirements.txt
scripts\.venv\Scripts\python -m playwright install chromium
copy scripts\scrapers\.env.example scripts\.env
```

Preencha `GEMINI_API_KEY` em `scripts/.env` (chave gratuita em
https://aistudio.google.com/apikey). O `.env` ja esta no `.gitignore`.

**Login (uma vez, manual):**

```powershell
scripts\.venv\Scripts\python scripts\scrapers\facebook_sjddoficial.py --setup
```

Abre o Chromium visivel. **Faca login com a sua conta e espere a pagina
carregar.** O perfil fica em `scripts/scrapers/fb_profile/` e esta no
`.gitignore` — ele contem cookies e local storage da sua conta, nunca versione.

**Reconhecimento (nao chama o LLM, nao gasta cota):**

```powershell
scripts\.venv\Scripts\python scripts\scrapers\facebook_sjddoficial.py --probe
```

Lista os titulos dos posts recentes, ja separados entre os que passaram no filtro
lexical e os que foram barrados. Leia antes de gastar: uma pagina que publica
mais aviso de servico do que ocorrencia de seguranca faz a fonte inteira nao
render.

**Filtro lexical:** antes de qualquer chamada ao Gemini, o texto do post passa por
um filtro de palavra-chave (`TERMOS_OCORRENCIA` no script) que procura os verbos
de ocorrencia — `assalt*`, `furto`, `roub*`, `agress*`, `briga`, `acidente`,
`tiroteio`, `desaparecid*`, `resgat*`, e assim por diante. Quem nao tem nenhum
termo e barrado sem gastar cota.

O filtro e conservador por desenho: ele so descarta quem nao tem **nenhum** termo,
e quem passa ainda pode ser rejeitado pelo LLM depois. Os termos de contexto
(`iluminacao`, `area deserta`) ficam de fora de proposito, porque aparecem em
texto institucional ("a iluminacao sera improveada") e puxariam o LLM para
classificar melhoria de obra como alerta.

Medido em 12 posts reais deste perfil: 5 passaram e 7 foram barrados, entre eles
eleicoes, patrocínio do governo, convocacao de doadores, resultado de futebol e
um post de bom dia. Dos 5 que passaram, 3 sao ocorrencia de seguranca real.

**Acervo bruto (`--collect`):** separa extracao de classificacao. Rola o feed
fundo, le o texto dos posts novos e grava tudo em
`scripts/data/facebook_sjddoficial_posts.json` **sem chamar o LLM** — portanto
sem gastar cota. E acumulativo: rodar de novo so le o que ainda nao esta no
arquivo, entao a meta (padrao `COLLECT_MAX_POSTS`, 1000) pode ser alcancada em
varias execucoes.

```powershell
scripts\.venv\Scripts\python scripts\scrapers\facebook_sjddoficial.py --collect
scripts\.venv\Scripts\python scripts\scrapers\facebook_sjddoficial.py --collect --max-posts 200 --workers 6
```

**Leitura paralela.** O gargalo e uma navegacao de pagina por post, nao CPU: por
isso a leitura roda em `--workers` navegadores independentes (padrao 4), cada um
autenticado pelo `storage_state` exportado do perfil persistente. Detalhe de
implementacao: um `user_data_dir` so aceita um contexto por vez e a API sync do
Playwright nao cruza threads, entao cada worker abre o *proprio* Chromium em vez
de compartilhar o perfil. A descoberta (rolagem) segue sequencial.

Medido em 2026-10-13: a descoberta **nao satura** e rende ~2,4 permalinks por
rolagem — 150 rolagens (~4 min) produziram 358 permalinks distintos. Mirar 1000
posts pede da ordem de 400 rolagens (~12 min) so de descoberta. Com 4 workers a
leitura caiu de ~4 s/post para menos da metade do tempo de parede (rodada de 21
posts novos em ~88 s, ja incluindo a descoberta). O acervo segue incremental:
acumule em varias rodadas em vez de tentar tudo de uma vez.

Como `_read_post` devolve `None` em post sem mensagem longa (imagem/video puro),
a descoberta vai ao dobro da meta (`COLLECT_DISCOVERY_FACTOR`), senao o acervo
pararia abaixo dela. Blocos de texto ofuscados pelo Facebook (letras embaralhadas
com o caractere invisivel U+034F, diferentes a cada render) sao descartados na
leitura e nao entram no acervo. Como os workers param de forma concorrente ao
bater a meta, o acervo pode passar dela em ate `--workers - 1` posts.

**Coleta:**

```powershell
scripts\.venv\Scripts\python scripts\scrapers\facebook_sjddoficial.py --dry-run
scripts\.venv\Scripts\python scripts\scrapers\facebook_sjddoficial.py --scrape
```

`--dry-run` imprime a classificacao de cada post sem gravar nada — use para
calibrar o prompt antes de rodar de verdade. `--scrape` grava em
`scripts/data/facebook_sjddoficial_reports.json`.

Opcoes: `--max-posts N` limita a coleta (padrao 30 no probe, 1000 no collect, 50 no scrape) e
`--headed` abre o navegador visivel para depurar. A taxa de chamadas ao LLM e
fixa e independe desse limite; ele so muda quantos posts cabem na rodada.

**Saida:** `scripts/data/facebook_sjddoficial_reports.json`, no mesmo esquema dos
outros scrapers, mais `tipo_perigo`, `confianca` e `justificativa`:

| Campo               | Descricao                                                      |
|---------------------|----------------------------------------------------------------|
| `titulo`            | Primeiros 120 caracteres do post                               |
| `descricao`         | Primeiras 2-3 frases; pronto para uso no populador             |
| `conteudo_completo` | Texto integral do post                                         |
| `endereco`          | Logradouro ou bairro que o LLM extraiu (pode ser `null`)       |
| `tipo_perigo`       | Um dos 12 valores de `TIPO_PERIGO_VALUES`                      |
| `confianca`         | Confianca do LLM, de 0 a 1                                     |
| `justificativa`     | Frase explicando a decisao, para auditoria manual              |
| `fonte_url`         | Permalink do post                                              |
| `fonte_data`        | Data de publicacao em ISO 8601                                 |

O script **nao gera `latitude` e `longitude`**, e a tabela `danger_reports` as
exige. Sem elas um registro fica invisivel no mapa admin e quebra a tela de
alertas. A geocodificacao do `endereco` ainda nao foi implementada; ver o
README do populator.

**Cobertura enviesada por construcao:** o perfil publica um feed de assinantes
em `/sjddoficial/supporters`, e `/groups/sjdd` responde "conteudo nao disponivel".
O feed publico nao expoe os posts — o que ele renderiza sao comentarios. Como
cada comentario carrega o permalink do post ao qual pertence, o scraper monta os
ids a partir deles. Isso significa que **apenas posts que receberam comentario
sao descobertos**; post silencioso nao aparece. Nao ha aba alternativa
(`/posts/`, `?sk=list` redirecionam para a inicial) que corrija isso. Ampliar a
coleta exige outra fonte, e nao mais rolagem.

**Volume extraido:** medido em 2026-09-29, a rolagem entrega cerca de 1 a 2 posts
novos por passo, de forma continua ate a pagina acabar. O coletor para ao atingir
`--max-posts` ou apos algumas rolagens seguidas sem post novo:

| Rolagens | Ids de post distintos |
|---|---|
| 5 | 9 |
| 15 | 23 |
| 30 | 45 |
| 45 | 57 |

A leitura e a seguinte: **extrair nao e o gargalo, a cota do LLM e.** Com 45
rolagens o coletor acha cerca de 57 posts, dos quais o filtro lexical deixa
tipicamente um terco. Como so 20 podem ser classificados por dia, a coleta pode
rodar com folga e generously: o limite que importa e quantos o Gemini aceita, e
nao quantos o Facebook entrega.

**Execucoes incrementais:** `scripts/data/.fb_seen.json` guarda os permalinks ja
tratados, e o script so paga por posts novos. Sem isso, reclassificar o
historico a cada execucao seria um custo recorrente desnecessario.

O que entra no arquivo depende do destino do post:

| Destino | Entra no `.fb_seen.json`? |
|---|---|
| Classificado como relevante | Sim |
| Barrado pelo filtro lexical | Sim, se o LLM nao parou por cota |
| Classificado e rejeitado pelo LLM | Sim |
| Nao classificado (falha de API ou cota no meio da fila) | **Nao** — sera retentado |

Quem ja foi classificado (relevante ou rejeitado) entra no arquivo mesmo quando a
cota acaba no meio da fila: esse post ja foi pago, e reconsulta-lo amanha
gastaria de novo a cota do dia. Ficam de fora apenas os candidatos que o Gemini
ainda nao respondeu — exatamente os que serao retentados.

A excecao do filtro lexical tambem e proposital. Ele e barato e deterministico,
entao rechecar o mesmo post amanha custaria uma rolagem do Facebook para chegar a
mesma conclusao. Quando a cota acaba no meio da fila, porem, a rodada nao
terminou, e o barrado volta na proxima execucao.

**Sessao expirada:** cookies do Facebook duram de 60 a 90 dias. Quando
expiram, o script **falha com mensagem explicita** em vez de devolver zero
posts — senao pareceria que a pagina simplesmente nao publicou. Se isso
aparecer, rode `--setup` de novo.

**Limites conhecidos:** existem dois tetos no Gemini, e eles nao se confundem.

| Limite | Valor no plano gratuito | Como o script reage |
|---|---|---|
| Requisições por minuto | ~15 RPM | Pausa de 5 s entre chamadas (12 RPM, com folga) |
| Requisições por **dia** | **20 por modelo** | Interrompe a fila e diz que volta amanhã |

O teto diário é o que aperta de verdade. O `RetryInfo` que a API devolve nesse
caso sugere 3s a 48s, o que é enganoso: a cota só se renova no dia seguinte.
Esperar esse tempo e reprocessar a fila inteira só produziria a mesma resposta
de erro N vezes, então o script detecta a métrica
`GenerateRequestsPerDayPerProjectPerModel-FreeTier`, interrompe na hora e deixa
os posts restantes para a próxima execução. Como o `.fb_seen.json` só grava o que
foi classificado, retomar depois não paga de novo pelo que já deu certo.

Na prática isso limita a **20 posts classificados por dia**, independentemente de
quantos posts o scraper coletar. Para acompanhar o consumo, veja AI Studio →
Usage.

Os 503 são sobrecarga do servidor do Google e são diferentes: esses se
resolvem com espera, e por isso têm retry com backoff exponencial de 3s, 6s, 12s
e 24s.

## Repeticao segura

Emboabas e G1 sobrescrevem seus arquivos JSON a cada execucao. O scraper SEJUSP
tambem substitui somente os CSVs filtrados no mesmo caminho; os CSVs originais
completos não são mantidos localmente. Todos os CSVs SEJUSP ficam diretamente em
`scripts/data/` e recursos diferentes permanecem em arquivos separados.

O scraper do Facebook se comporta de forma diferente: ele **acrescenta** ao JSON
existente, deduplicando por `fonte_url`, e mantem o registro do que ja foi
classificado em `.fb_seen.json`. Rodar duas vezes nao duplica entradas.

## Validacao sem acessar a internet

```powershell
py -m py_compile scripts\scrapers\emboabas.py
py -m py_compile scripts\scrapers\sejusp.py
scripts\.venv\Scripts\python -m py_compile scripts\scrapers\facebook_sjddoficial.py
```
