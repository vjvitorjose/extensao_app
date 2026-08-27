# Populacao do banco

Este diretorio (scripts/) possui scripts Python para criar dados ficticios no Supabase durante o desenvolvimento.

## Pre-requisitos

- Python 3.10 ou superior.
- Projeto Supabase configurado.
- Arquivo `.env` na raiz do projeto contendo:

```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_ANON_KEY=sua-chave-anon
SUPABASE_SERVICE_ROLE_KEY=sua-chave-service-role
```

A `SUPABASE_SERVICE_ROLE_KEY` é necessaria porque os scripts acessam a API administrativa do Supabase Auth. Ela deve ser usada somente em scripts locais ou em ambiente seguro, nunca no aplicativo Flutter distribuido.

Os scripts carregam automaticamente as variaveis do arquivo `.env` e nao substituem variaveis que ja estejam definidas no ambiente.

## Ordem recomendada

Execute os scripts nesta ordem:

```powershell
py scripts\user-populator.py
py scripts\emergency-contact-populator.py
py scripts\danger-report-populator.py
```

O primeiro script cria os usuarios que os dois scripts seguintes usam como referencia.

## 1. Usuarios artificiais

Arquivo: `user-populator.py`

O script gera 1000 usuarios ficticios:

- 5 usuarios base com nomes, telefones, CPFs, e-mails e senhas definidos no codigo.
- 995 usuarios gerados a partir de combinacoes de nomes brasileiros.
- Nomes sem numeros e sem repeticao.
- Telefones brasileiros ficticios e unicos.
- CPFs ficticios com digitos verificadores validos e unicos.
- E-mails e senhas unicos para teste.

Antes de criar uma conta, o script lista os usuarios existentes no Auth e procura pelo e-mail. Usuarios ja existentes nao sao criados novamente. O perfil em `profiles` e salvo com `upsert`, usando o mesmo `id` da conta Auth.

O script atualiza `profiles` com:

- `id`
- `nome_completo`
- `telefone`
- `cpf`

## 2. Contatos de emergencia

Arquivo: `emergency-contact-populator.py`

Para cada um dos 1000 usuarios artificiais, o script seleciona os dois usuarios seguintes da lista como contatos, em rotacao. Por exemplo, os contatos do primeiro usuario sao o segundo e o terceiro; os contatos do ultimo sao o primeiro e o segundo.

Esse modelo garante que:

- Cada usuario recebe 2 contatos.
- Ninguem e usado como contato de todos os usuarios.
- Um usuario nao e contato de si mesmo.
- Os contatos sao distribuidos entre toda a base.
- Uma nova execucao nao duplica contatos existentes.

Os dados dos contatos sao gravados em `emergency_contacts`:

- `profile_id`: usuario que possui o contato.
- `nome`: nome do usuario contato.
- `telefone`: telefone do perfil do contato.
- `email`: e-mail do contato.
- `parentesco`: sempre `Amigo`.

## 3. Alertas artificiais

Arquivo: `danger-report-populator.py`

Cada execucao:

1. Carrega os 1000 usuarios definidos por `user-populator.py`.
2. Confirma que todos existem no Supabase Auth.
3. Seleciona exatamente 5 usuarios aleatorios e distintos.
4. Gera de 1 a 3 alertas para cada usuario selecionado.
5. Escolhe tipos diferentes para um mesmo usuario.
6. Gera coordenadas aleatorias concentradas na area urbana de Sao Joao del-Rei, MG.
7. Insere os registros em `danger_reports`.

Assim, cada execucao cria entre 5 e 15 alertas. Os alertas nao sao deduplicados: executar o script novamente cria novos registros, mesmo para usuarios que ja receberam alertas.

Os tipos usados sao:

- `assedio`
- `iluminacao_ruim`
- `perseguicao`
- `area_deserta`
- `acidente_transito`
- `assalto`
- `furto`
- `violencia_fisica`
- `presenca_arma`
- `incendio`
- `via_bloqueada`
- `emergencia_medica`

Cada registro inclui:

- `usuario_id`
- `tipo_perigo`
- `descricao`
- `latitude`
- `longitude`
- `endereco`

As coordenadas sao ficticias. O script usa limites aproximados da area urbana, nao o poligono oficial do municipio.

### Coordenadas e distancia

O centro de referencia usado pelo gerador e:

- Latitude: `-21.1355`
- Longitude: `-44.2616`

Cada coordenada e gerada por uma distribuicao normal ao redor desse centro:

- Dispersao de latitude: `0.012` graus, aproximadamente `1,3 km`.
- Dispersao de longitude: `0.014` graus, aproximadamente `1,5 km`.

Depois da geracao, os valores sao limitados a esta caixa urbana aproximada:

- Latitude minima: `-21.17`
- Latitude maxima: `-21.10`
- Longitude minima: `-44.30`
- Longitude maxima: `-44.22`

Considerando o centro e o canto mais distante dessa caixa, a distancia maxima aproximada e de `5,8 km`. A caixa é um limite retangular aproximado; ela nao representa o limite administrativo oficial do municipio.

## Rate limiting

Todos os scripts limitam as requisicoes HTTP ao Supabase:

- Padrao: 2 requisicoes por segundo.
- O limite e aplicado antes de cada tentativa.
- Respostas HTTP `429` sao repetidas ate 5 vezes.
- O header `Retry-After` e respeitado quando fornecido.

No `user-populator.py`, o limite pode ser alterado pelo ambiente:

```powershell
$env:SUPABASE_REQUESTS_PER_SECOND="1"
py scripts\user-populator.py
```

Os outros scripts usam atualmente o limite fixo de 2 requisicoes por segundo.

## Repeticao segura

- `user-populator.py`: pode ser executado novamente; usuarios existentes sao reutilizados e os perfis sao atualizados.
- `emergency-contact-populator.py`: pode ser executado novamente; contatos existentes sao ignorados.
- `danger-report-populator.py`: nao e idempotente; cada execucao adiciona novos alertas.

## Validacao sem acessar o banco

Para verificar a sintaxe de um script sem executar sua funcao principal:

```powershell
py -m py_compile scripts\user-populator.py
py -m py_compile scripts\emergency-contact-populator.py
py -m py_compile scripts\danger-report-populator.py
```

Esses comandos apenas compilam os arquivos e nao fazem requisicoes ao Supabase.
