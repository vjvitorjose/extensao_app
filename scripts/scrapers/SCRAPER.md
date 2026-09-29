# Scrapers

Este diretorio (`scripts/scrapers/`) possui três scripts Python independentes para
coletar dados reais de fontes publicas. Emboabas e G1 geram arquivos JSON; a
SEJUSP gera arquivos CSV filtrados para Sao Joao del-Rei.

Os dados coletados ficam em `scripts/data/` (pasta ignorada pelo Git, pois
contem conteudo de terceiros).

## Pre-requisitos

- Python 3.10 ou superior.
- Sem dependencias externas: todos os scrapers usam apenas a stdlib do Python.
- Conexao com a internet no momento da execucao.

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

> O campo `tipo_perigo` **nao e gerado pelo scraper**. A classificacao
> ficara a cargo de uma LLM que consumira o `conteudo_completo` futuramente.

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

## Repeticao segura

Emboabas e G1 sobrescrevem seus arquivos JSON a cada execucao. O scraper SEJUSP
tambem substitui somente os CSVs filtrados no mesmo caminho; os CSVs originais
completos não são mantidos localmente. Todos os CSVs SEJUSP ficam diretamente em
`scripts/data/` e recursos diferentes permanecem em arquivos separados.

## Validacao sem acessar a internet

```powershell
py -m py_compile scripts\scrapers\emboabas.py
py -m py_compile scripts\scrapers\sejusp.py
```
