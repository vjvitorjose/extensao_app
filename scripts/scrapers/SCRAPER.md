# Scrapers

Este diretorio (scripts/scrapers/) possui scripts Python para coletar dados
reais de fontes publicas e gerar arquivos JSON consumidos pelos populators.

Os dados coletados ficam em `scripts/data/` (pasta ignorada pelo Git, pois
contem conteudo de terceiros).

## Pre-requisitos

- Python 3.10 ou superior.
- Sem dependencias externas: todos os scrapers usam apenas a stdlib do Python.
- Conexao com a internet no momento da execucao.

## Ordem recomendada

Execute os scrapers antes dos populators, a partir da raiz do projeto:

```powershell
# Coleta ocorrencias de seguranca publica do Emboabas
py scripts\scrapers\emboabas.py
```

Depois, execute os populators normalmente (veja `scripts/populators/POPULATOR.md`).

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
| `conteudo_completo` | Texto integral do artigo (para uso futuro com LLM)             |
| `tipo_perigo`       | Classificado por palavras-chave (12 tipos do banco)            |
| `endereco`          | Bairro/rua extraido por regex do conteudo (pode ser `null`)    |
| `fonte_url`         | URL do artigo original                                         |
| `fonte_data`        | Data de publicacao (ISO 8601)                                  |

**Configuracao:**

```python
# Quantidade de posts por categoria (padrao: 100)
POSTS_PER_CATEGORY = 100
```

**Classificacao por palavras-chave:**

O campo `tipo_perigo` é inferido automaticamente a partir do titulo e conteudo.
A classificacao é heuristica e pode conter falsos positivos — o campo
`conteudo_completo` esta disponivel justamente para permitir re-classificacao
via LLM no futuro.

**Execucao:**

```powershell
py scripts\scrapers\emboabas.py
```

**Rate limiting:** pausa de 0,5 s entre paginas; respostas HTTP 429 sao
repetidas ate 3 vezes respeitando o header `Retry-After`.

## Repeticao segura

Todos os scrapers sobrescrevem o arquivo de saida a cada execucao. Nao ha
deduplicacao entre execucoes: rodar novamente gera um JSON atualizado com os
posts mais recentes.

## Validacao sem acessar a internet

```powershell
py -m py_compile scripts\scrapers\emboabas.py
```
