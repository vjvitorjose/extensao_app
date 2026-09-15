"""Scraper da API WordPress do Emboabas para coletar ocorrencias de seguranca publica.

Fonte: https://emboabas.com (Radio Emboabas - Sao Joao del-Rei, MG)
Metodo: WordPress REST API (sem dependencias externas, apenas stdlib)

Categorias coletadas:
  - id=66  "Policial"  (591 posts) - ocorrencias policiais locais
  - id=10  "Cidade"    (729 posts) - noticias gerais com acidentes etc.

Execucao:
    py scripts\\scrapers\\emboabas.py

Saida:
    scripts\\data\\emboabas_danger_reports.json

O arquivo gerado e lido por danger-report-populator.py para enriquecer as
descricoes e enderecos dos alertas ficticios.
"""

import html
import json
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# ---------------------------------------------------------------------------
# Configuracao
# ---------------------------------------------------------------------------

BASE_URL = "https://emboabas.com/wp-json/wp/v2"
USER_AGENT = "vigIA-scraper/1.0 (desenvolvimento local)"

# Categorias de interesse para danger_reports.
# Chave: id da categoria no WordPress. Valor: nome legivel.
TARGET_CATEGORIES = {
    66: "Policial",
    10: "Cidade",
}

# Quantos posts buscar por categoria.
POSTS_PER_CATEGORY = 100

# Campos retornados pela API (reduz payload).
API_FIELDS = "id,date,link,title,content"

# Mapeamento: palavras-chave no titulo/conteudo -> tipo_perigo do banco.
# A ordem importa: a primeira correspondencia vence.
KEYWORD_MAP = (
    (("assedio", "assédio", "importunacao", "importunação"), "assedio"),
    (("perseguicao", "perseguição", "perseguido"), "perseguicao"),
    (("assalto", "assaltado", "roubado", "roubo"), "assalto"),
    (("furto", "furtado", "subtrai"), "furto"),
    (("homicidio", "homicídio", "assassinado", "assassinato", "baleado", "esfaqueado"), "violencia_fisica"),
    (("arma", "revolver", "revólver", "pistola", "faca"), "presenca_arma"),
    (("incendio", "incêndio", "fumaca", "fumaça", "fogo"), "incendio"),
    (("acidente", "colisao", "colisão", "atropelado", "atropelamento"), "acidente_transito"),
    (("bloqueada", "bloqueado", "interditada", "interdita"), "via_bloqueada"),
    (("samu", "socorro", "emergencia medica", "emergência médica"), "emergencia_medica"),
    (("iluminacao", "iluminação", "escuro", "luz"), "iluminacao_ruim"),
)

# Diretorio de saida (relativo ao arquivo do scraper).
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data"
OUTPUT_FILE = OUTPUT_DIR / "emboabas_danger_reports.json"

# ---------------------------------------------------------------------------
# Utilitarios
# ---------------------------------------------------------------------------


def _strip_html(text: str) -> str:
    """Remove tags HTML e normaliza espacos."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _classify(title: str, content: str) -> str:
    """Infere o tipo_perigo a partir do titulo e conteudo do artigo.

    Usa word boundary (\\b) para evitar falsos positivos por substring,
    por exemplo 'armazenados' nao deve disparar 'presenca_arma'.
    """
    haystack = (title + " " + content).lower()
    for keywords, tipo in KEYWORD_MAP:
        pattern = "|".join(rf"\b{re.escape(kw)}\b" for kw in keywords)
        if re.search(pattern, haystack):
            return tipo
    return "area_deserta"  # fallback


def _extract_address(content: str) -> str | None:
    """Tenta extrair o primeiro endereco/bairro mencionado no conteudo.

    Estrategia simples: procura padroes comuns como
      'na Rua X'  'na Avenida X'  'no bairro X'  'na Praca X'
    e retorna o trecho encontrado (ate ~100 chars).
    """
    patterns = [
        r"(?:na|no|ao)\s+(Rua|Avenida|Praça|Praca|Bairro|Rodovia|Estrada|BR[-\s]?\d+)[^,.;\n]{3,60}",
        r"(?:no bairro|no Bairro)\s+[A-ZÀ-Ü][^\n,.;:]{3,50}",
        r"(?:região|regiao)\s+d[oa]\s+[A-ZÀ-Ü][^\n,.;:]{3,40}",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            found = match.group().strip()
            found = re.sub(
                r"\s+(e|em|de|da|do|quando|onde)\s*$", "", found, flags=re.IGNORECASE
            )
            if len(found) <= 100:
                return found + ", São João del-Rei, MG"
    return None


# ---------------------------------------------------------------------------
# Requisicoes
# ---------------------------------------------------------------------------


def _fetch_json(url: str, retries: int = 3) -> list | dict:
    for attempt in range(retries):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 429 and attempt < retries - 1:
                retry_after = float(exc.headers.get("Retry-After", "2"))
                time.sleep(max(retry_after, 2.0))
            else:
                raise
        except URLError:
            if attempt < retries - 1:
                time.sleep(2.0)
            else:
                raise
    raise RuntimeError("Numero maximo de tentativas excedido.")


def _fetch_posts(category_id: int, per_page: int = POSTS_PER_CATEGORY) -> list[dict]:
    """Busca posts de uma categoria pela WP REST API (paginado)."""
    results = []
    page = 1
    while True:
        url = (
            f"{BASE_URL}/posts"
            f"?categories={category_id}"
            f"&per_page={min(per_page - len(results), 100)}"
            f"&page={page}"
            f"&_fields={API_FIELDS}"
        )
        posts = _fetch_json(url)
        if not isinstance(posts, list) or not posts:
            break
        results.extend(posts)
        if len(results) >= per_page or len(posts) < 100:
            break
        page += 1
        time.sleep(0.5)  # cortesia com o servidor
    return results[:per_page]


# ---------------------------------------------------------------------------
# Processamento
# ---------------------------------------------------------------------------


def _build_descricao(content: str, max_chars: int = 350) -> str:
    """Extrai as primeiras frases do conteudo ate atingir max_chars caracteres.

    O excerpt do WordPress e gerado automaticamente a partir da primeira frase,
    entao e equivalente a pegar so a primeira frase. Esta funcao coleta frases
    do conteudo completo ate ter contexto suficiente sobre a ocorrencia.
    """
    sentences = re.split(r"(?<=[.!?])\s+", content)
    descricao = ""
    for sentence in sentences:
        candidate = (descricao + " " + sentence).strip() if descricao else sentence
        if len(candidate) > max_chars and descricao:
            # Ja tem contexto suficiente; nao adiciona mais
            break
        descricao = candidate
        if len(descricao) >= max_chars:
            break
    return descricao.strip()


def _process_post(post: dict) -> dict:
    """Converte um post WordPress numa entrada para danger_reports.

    Campos gerados:
      titulo            - titulo do artigo
      descricao         - primeiras 2-3 frases; pronto para uso no populador
      conteudo_completo - artigo integral limpo; para uso futuro com LLM
      tipo_perigo       - classificado por palavras-chave
      endereco          - bairro/rua extraido por regex (pode ser None)
      fonte_url         - URL original
      fonte_data        - data de publicacao (ISO 8601)
    """
    title = _strip_html(post["title"]["rendered"])
    content = _strip_html(post["content"]["rendered"])

    descricao = _build_descricao(content)
    tipo = _classify(title, content)
    endereco = _extract_address(content)

    return {
        "titulo": title,
        "descricao": descricao,
        "conteudo_completo": content,
        "tipo_perigo": tipo,
        "endereco": endereco,
        "fonte_url": post["link"],
        "fonte_data": post["date"],
    }


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------


def scrape() -> None:
    """Executa o scraping e salva o resultado em JSON."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_entries: list[dict] = []
    seen_urls: set[str] = set()

    for cat_id, cat_name in TARGET_CATEGORIES.items():
        print(f"[emboabas] Buscando categoria '{cat_name}' (id={cat_id})...")
        posts = _fetch_posts(cat_id)
        print(f"  {len(posts)} posts recebidos.")

        for post in posts:
            url = post.get("link", "")
            if url in seen_urls:
                continue
            seen_urls.add(url)

            entry = _process_post(post)
            # Filtra posts sem descricao util (ex: apenas podcasts sem texto)
            if len(entry["descricao"]) < 30:
                continue
            all_entries.append(entry)

    print(f"\n[emboabas] Total de entradas uteis geradas: {len(all_entries)}")

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=2)

    print(f"[emboabas] Salvo em: {OUTPUT_FILE}")


if __name__ == "__main__":
    try:
        scrape()
    except (HTTPError, URLError) as exc:
        detail = exc.read().decode("utf-8") if isinstance(exc, HTTPError) else str(exc)
        raise RuntimeError(f"Falha na comunicacao com o Emboabas: {detail}") from exc
