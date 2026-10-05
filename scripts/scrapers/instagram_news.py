"""Scraper de perfis de Instagram para noticias de Sao Joao del-Rei.

Fonte: Instagram (perfis de noticias locais)
Metodo: instaloader (biblioteca Python para scraping de Instagram)

Perfis monitorados:
  - popnewsjdr      : Noticias gerais da cidade
  - sjdr.prefeitura : Comunicados oficiais da prefeitura

Execucao:
    py scripts\\scrapers\\instagram_news.py

Saida:
    scripts\\data\\instagram_news_reports.json

O arquivo gerado e lido pelo danger-report-populator.py para criar
relatos de perigo no Supabase a partir de noticias reais.

Autenticacao (opcional mas recomendada):
    Para evitar bloqueios do Instagram, configure as credenciais via
    variaveis de ambiente ou arquivo .env:

    INSTAGRAM_LOGIN=seu_usuario
    INSTAGRAM_PASSWORD=sua_senha

    Sem login, o Instagram frequentemente retorna HTTP 429 (Too Many Requests).
"""

import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import instaloader

# ---------------------------------------------------------------------------
# Configuracao
# ---------------------------------------------------------------------------

TARGET_PROFILES = [
    "popnewsjdr",
    "sjdr.prefeitura",
]

MAX_POSTS_PER_PROFILE = 50
MAX_DAYS_OLD = 30

# Palavras-chave para filtrar noticias relevantes de Sao Joao del-Rei
RELEVANT_KEYWORDS = [
    "são joão del rei", "sao joao del rei", "são joão del-rei", "sao joao del-rei",
    "sjdr", "são joão", "sao joao",
    "assalto", "roubo", "furto", "assediado", "assedio",
    "acidente", "colisão", "colisao", "batida", "atropelamento",
    "incêndio", "incendio", "fogo", "queimada",
    "violência", "violencia", "agressão", "agressao", "espancamento",
    "arma", "tiroteio", "disparo", "tiro",
    "perigo", "emergência", "emergencia",
    "polícia", "policia", "bombeiros", "hospital", "ambulância", "ambulancia",
    "perseguição", "persegucao", "perseguido",
    "bloqueada", "interdição", "interdicao", "via fechada",
    "iluminação", "iluminacao", "poste apagado", "luz apagada",
    "deserta", "deserto", "pouco movimento",
    "centro", "bairro", "rua", "avenida", "praça", "praca",
]

# Mapeamento de palavras-chave para tipos de perigo
DANGER_TYPE_KEYWORDS = {
    "assedio": ["assedio", "assediado", "abordagem", "abordado"],
    "furto": ["furto", "roubo", "subtração", "subtracao", "levou", "levaram"],
    "acidente_transito": ["acidente", "colisão", "colisao", "batida", "atropelamento", "capotou"],
    "incendio": ["incêndio", "incendio", "fogo", "queimada", "chamas", "fumaça", "fumaca"],
    "presenca_arma": ["arma", "tiroteio", "disparo", "tiro", "revólver", "revolver", "pistola"],
    "violencia_fisica": ["violência", "violencia", "agressão", "agressao", "espancamento", "soco", "chute"],
    "perseguicao": ["perseguição", "persegucao", "perseguido", "fuga", "fugiram"],
    "via_bloqueada": ["bloqueada", "interdição", "interdicao", "via fechada", "fechada", "bloqueio"],
    "emergencia_medica": ["emergência", "emergencia", "ambulância", "ambulancia", "hospital", "atendimento", "caído", "caido"],
    "iluminacao_ruim": ["iluminação", "iluminacao", "poste apagado", "luz apagada", "escuro", "apagado"],
    "area_deserta": ["deserta", "deserto", "pouco movimento", "vazio", "vazia"],
}

# Bairros e regioes de Sao Joao del-Rei para validacao
SJDR_NEIGHBORHOODS = [
    "centro", "são francisco", "sao francisco", "fábricas", "fabricas",
    "santo antônio", "santo antonio", "nossa senhora do carmo", "carmo",
    "são josé", "sao jose", "são sebastião", "sao sebastiao",
    "são bento", "sao bento", "são joão", "sao joao",
    "nossa senhora da conceição", "conceicao", "nossa senhora do rosário", "rosario",
    "nossa senhora de fátima", "fatima", "nossa senhora de lourdes", "lourdes",
    "santa terezinha", "santa teresa", "santa cruz",
    "vila santiago", "vila são joão", "vila sao joao",
    "jardim das flores", "jardim", "parque", "residencial",
    "bom jesus", "sagrada familia", "sagrada família",
    "dom bosco", "são domingos", "sao domingos",
    "alto da boa vista", "boa vista", "vista alegre",
    "matozinhos", "ritápolis", "ritapolis", "tiradentes",
]

# Diretorio de saida
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data"
OUTPUT_FILE = OUTPUT_DIR / "instagram_news_reports.json"

# Limites aproximados da area urbana de Sao Joao del-Rei, MG
URBAN_LATITUDE_MIN = -21.17
URBAN_LATITUDE_MAX = -21.10
URBAN_LONGITUDE_MIN = -44.30
URBAN_LONGITUDE_MAX = -44.22
URBAN_CENTER_LATITUDE = -21.1355
URBAN_CENTER_LONGITUDE = -44.2616

# Configuracao de rate limiting
REQUEST_DELAY = 2  # segundos entre requisicoes
PROFILE_DELAY = 5  # segundos entre perfis
MAX_RETRIES = 3  # tentativas em caso de erro
RETRY_DELAY = 60  # segundos de espera apos erro


# ---------------------------------------------------------------------------
# Utilitarios
# ---------------------------------------------------------------------------


def _load_dotenv() -> None:
    """Carrega variaveis de ambiente do arquivo .env se existir."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"\''))


def _is_relevant_post(caption: str) -> bool:
    """Verifica se a legenda contem palavras-chave relevantes."""
    if not caption:
        return False
    caption_lower = caption.lower()
    return any(keyword in caption_lower for keyword in RELEVANT_KEYWORDS)


def _is_from_sjdr(caption: str) -> bool:
    """Verifica se a legenda menciona Sao Joao del-Rei ou bairros da cidade."""
    if not caption:
        return False
    caption_lower = caption.lower()
    sjdr_mentions = [
        "são joão del rei", "sao joao del rei", "são joão del-rei", "sao joao del-rei",
        "sjdr", "são joão", "sao joao",
    ]
    if any(mention in caption_lower for mention in sjdr_mentions):
        return True
    return any(neighborhood in caption_lower for neighborhood in SJDR_NEIGHBORHOODS)


def _classify_danger_type(caption: str) -> str | None:
    """Classifica o tipo de perigo baseado em palavras-chave da legenda."""
    if not caption:
        return None
    caption_lower = caption.lower()
    for danger_type, keywords in DANGER_TYPE_KEYWORDS.items():
        if any(keyword in caption_lower for keyword in keywords):
            return danger_type
    return None


def _extract_address(caption: str) -> str | None:
    """Tenta extrair endereco/bairro mencionado na legenda."""
    if not caption:
        return None

    patterns = [
        r"(?:na|no|ao)\s+(Rua|Avenida|Praça|Praca|Bairro|Rodovia|Estrada|BR[-\s]?\d+)[^,.;\n]{3,60}",
        r"(?:no bairro|no Bairro)\s+[A-ZÀ-Ü][^\n,.;:]{3,50}",
        r"(?:região|regiao)\s+d[oa]\s+[A-ZÀ-Ü][^\n,.;:]{3,40}",
    ]
    for pattern in patterns:
        match = re.search(pattern, caption, re.IGNORECASE)
        if match:
            found = match.group().strip()
            found = re.sub(
                r"\s+(e|em|de|da|do|quando|onde)\s*$", "", found, flags=re.IGNORECASE
            )
            if len(found) <= 100:
                return found + ", São João del-Rei, MG"
    return None


def _build_descricao(caption: str, max_chars: int = 350) -> str:
    """Extrai as primeiras frases da legenda ate atingir max_chars caracteres."""
    sentences = re.split(r"(?<=[.!?])\s+", caption)
    descricao = ""
    for sentence in sentences:
        candidate = (descricao + " " + sentence).strip() if descricao else sentence
        if len(candidate) > max_chars and descricao:
            break
        descricao = candidate
        if len(descricao) >= max_chars:
            break
    return descricao.strip()


def _generate_random_coordinates() -> tuple[float, float]:
    """Gera coordenadas aleatorias na area urbana de Sao Joao del-Rei."""
    import random
    latitude = random.gauss(URBAN_CENTER_LATITUDE, 0.012)
    longitude = random.gauss(URBAN_CENTER_LONGITUDE, 0.014)
    latitude = min(max(latitude, URBAN_LATITUDE_MIN), URBAN_LATITUDE_MAX)
    longitude = min(max(longitude, URBAN_LONGITUDE_MIN), URBAN_LONGITUDE_MAX)
    return round(latitude, 6), round(longitude, 6)


def _login(loader: instaloader.Instaloader) -> bool:
    """Tenta fazer login no Instagram se as credenciais estiverem disponiveis."""
    _load_dotenv()
    username = os.environ.get("INSTAGRAM_LOGIN")
    password = os.environ.get("INSTAGRAM_PASSWORD")

    if not username or not password:
        print("[instagram] Credenciais nao encontradas. Executando sem login.")
        print("  Para evitar bloqueios, defina INSTAGRAM_LOGIN e INSTAGRAM_PASSWORD no .env")
        return False

    try:
        loader.login(username, password)
        print(f"[instagram] Login realizado como '{username}'.")
        return True
    except instaloader.exceptions.BadCredentialsException:
        print("[instagram] Erro: credenciais invalidas.")
        return False
    except instaloader.exceptions.ConnectionException as exc:
        print(f"[instagram] Erro de conexao no login: {exc}")
        return False


def _scrape_profile(loader: instaloader.Instaloader, username: str) -> list[dict]:
    """Coleta posts de um perfil do Instagram."""
    print(f"[instagram] Buscando perfil '{username}'...")

    for attempt in range(MAX_RETRIES):
        try:
            profile = instaloader.Profile.from_username(loader.context, username)
            break
        except instaloader.exceptions.ProfileNotExistsException:
            print(f"  Perfil '{username}' nao encontrado.")
            return []
        except instaloader.exceptions.TooManyRequestsException:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (attempt + 1)
                print(f"  Muitas requisicoes. Aguardando {wait_time}s antes de tentar novamente...")
                time.sleep(wait_time)
            else:
                print(f"  Erro: muitas requisicoes. Tente novamente mais tarde.")
                return []
        except instaloader.exceptions.ConnectionException as exc:
            if attempt < MAX_RETRIES - 1:
                print(f"  Erro de conexao: {exc}. Tentando novamente...")
                time.sleep(RETRY_DELAY)
            else:
                print(f"  Erro de conexao ao buscar perfil '{username}': {exc}")
                return []

    posts = []
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=MAX_DAYS_OLD)

    try:
        for post in profile.get_posts():
            if len(posts) >= MAX_POSTS_PER_PROFILE:
                break

            # Ignorar posts muito antigos
            post_date = post.date_utc if post.date_utc else post.date
            if post_date < cutoff_date:
                continue

            caption = post.caption if post.caption else ""

            # Filtrar por relevancia e localidade
            if not _is_relevant_post(caption):
                continue
            if not _is_from_sjdr(caption):
                continue

            # Extrair localizacao marcada (se houver)
            location = None
            if post.location:
                location = {
                    "nome": post.location.name,
                    "latitude": post.location.lat,
                    "longitude": post.location.lng,
                }

            entry = {
                "titulo": caption[:100] if caption else "Sem titulo",
                "descricao": _build_descricao(caption),
                "conteudo_completo": caption,
                "endereco": _extract_address(caption),
                "fonte_url": f"https://www.instagram.com/p/{post.shortcode}/",
                "fonte_data": post_date.isoformat() if post_date else None,
                "fonte_perfil": username,
                "tipo_midia": "video" if post.is_video else "carousel" if post.typename == "GraphSidecar" else "imagem",
                "localizacao_marcada": location,
                "tipo_perigo": _classify_danger_type(caption),
            }
            posts.append(entry)
            print(f"  Post relevante: {entry['titulo'][:60]}...")

            # Cortesia com o servidor
            time.sleep(REQUEST_DELAY)

    except instaloader.exceptions.TooManyRequestsException:
        print(f"  Muitas requisicoes durante a coleta. Parando perfil '{username}'.")
    except instaloader.exceptions.ConnectionException as exc:
        print(f"  Erro de conexao ao coletar posts: {exc}")

    print(f"  {len(posts)} posts relevantes encontrados em '{username}'.")
    return posts


def scrape() -> None:
    """Executa o scraping e salva o resultado em JSON."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
    )

    # Tenta fazer login (recomendado para evitar bloqueios)
    _login(loader)

    all_entries: list[dict] = []
    seen_urls: set[str] = set()

    for username in TARGET_PROFILES:
        posts = _scrape_profile(loader, username)
        for entry in posts:
            url = entry.get("fonte_url", "")
            if url in seen_urls:
                continue
            seen_urls.add(url)
            all_entries.append(entry)

        # Pausa entre perfis
        time.sleep(PROFILE_DELAY)

    print(f"\n[instagram] Total de entradas uteis geradas: {len(all_entries)}")

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=2)

    print(f"[instagram] Salvo em: {OUTPUT_FILE}")


if __name__ == "__main__":
    scrape()
