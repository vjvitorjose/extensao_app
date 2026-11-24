"""Scraper de um perfil de noticias do municipio no Facebook.

Fonte: https://www.facebook.com/sjddoficial
Metodo: Playwright (Chromium) com perfil autenticado, filtro lexical e depois
        classificacao por LLM (Gemini) para decidir o que vira alerta de seguranca.

A fonte e um perfil pessoal de newspapel local, nao a Pagina oficial da
prefeitura. Ele mantem um feed de assinantes (`/sjddoficial/supporters`) que nao
e acessivel, e o feed publico nao expoe os posts: o que ele renderiza sao
comentarios. Como cada comentario carrega o permalink do post ao qual pertence,
os ids sao montados a partir deles. Consequencia: apenas posts que receberam
comentario sao descobertos.

O Facebook nao oferece API publica para leitura de paginas de terceiros: a
Graph API exige app review para `pages_read_engagement` e o RSS publico foi
removido em 2019. Por isso este scraper depende de um perfil de navegador real,
com login feito a mao uma unica vez.

Execucao:
    # 1. Uma vez so: abre o navegador e voce loga na sua conta
    py scripts\\scrapers\\facebook_sjddoficial.py --setup

    # 2. Reconhecimento: dumpa titulos sem chamar o LLM, ja separados entre os
    #    que passaram no filtro lexical e os barrados
    py scripts\\scrapers\\facebook_sjddoficial.py --probe

    # 3. Acervo bruto: acumula posts sem classificar (nao gasta cota do LLM).
    #    Rode varias vezes para juntar volume; a meta padrao e 1000. A leitura
    #    roda em paralelo (--workers, padrao 4) porque uma navegacao por post e
    #    o gargalo; a descoberta continua sequencial.
    py scripts\\scrapers\\facebook_sjddoficial.py --collect
    py scripts\\scrapers\\facebook_sjddoficial.py --collect --workers 6

    # 4. Coleta real (classifica o que passou no filtro lexical)
    py scripts\\scrapers\\facebook_sjddoficial.py --scrape
    py scripts\\scrapers\\facebook_sjddoficial.py --dry-run

    # 5. Classifica o acervo do passo 3 sem raspar de novo. Nao abre navegador:
    #    reaproveita o texto salvo e gasta so a cota do LLM (20/dia). Rode ao
    #    longo dos dias para consumir o acervo aos poucos.
    py scripts\\scrapers\\facebook_sjddoficial.py --classify

Saida:
    scripts\\data\\facebook_sjddoficial_reports.json   (--scrape)
    scripts\\data\\facebook_sjddoficial_probe.json     (--probe)
    scripts\\data\\facebook_sjddoficial_posts.json     (--collect)
    scripts\\data\\.fb_seen.json                       (permalink ja classificado)

A sessao do Facebook expira em 60-90 dias. Quando isso acontecer, o script
falha com mensagem explicita e nao em silencio: rode `--setup` de novo.
"""

import argparse
import json
import os
import re
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Configuracao
# ---------------------------------------------------------------------------

DEFAULT_PAGE_URL = "https://www.facebook.com/sjddoficial"

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data"
OUTPUT_FILE = OUTPUT_DIR / "facebook_sjddoficial_reports.json"
PROBE_FILE = OUTPUT_DIR / "facebook_sjddoficial_probe.json"
SEEN_FILE = OUTPUT_DIR / ".fb_seen.json"
# Acervo bruto do modo --collect: posts lidos e guardados SEM classificacao,
# para o volume acumular entre execucoes independentemente da cota do LLM.
POSTS_FILE = OUTPUT_DIR / "facebook_sjddoficial_posts.json"

# Perfil do Chromium com a sessao do Facebook. Fica ao lado deste arquivo e
# esta no .gitignore: ele contem cookies e local storage da sua conta.
PROFILE_DIR = Path(__file__).resolve().parent / "fb_profile"


class CotaDiariaEsgotada(RuntimeError):
	"""O plano gratuito do Gemini acabou as requisicoes do dia.

	Tipo proprio, separado de RuntimeError, porque o operador precisa poder
	distinguir "a API esta instavel, tente de novo em instantes" de "acabou
	hoje, volte amanha". Quem nao got this espera horas sem motivo.
	"""


# Valores aceitos por danger_reports.tipo_perigo. Esta lista e a mesma de
# REPORT_TYPES em scripts/populators/danger-report-populator.py. O enum real
# foi criado a mao no console do Supabase (ver supabase/migrations/0003) e nao
# esta documentado em lugar nenhum do repo, entao se divergir o gravacao vai
# falhar no banco e nao aqui.
TIPO_PERIGO_VALUES = (
	"assedio",
	"iluminacao_ruim",
	"perseguicao",
	"area_deserta",
	"acidente_transito",
	"assalto",
	"furto",
	"violencia_fisica",
	"presenca_arma",
	"incendio",
	"via_bloqueada",
	"emergencia_medica",
)

GEMINI_MODEL = "gemini-3.8-flash"

# Segmentos que identificam o tipo de post na URL do Facebook.
POST_PATH_KINDS = frozenset({"posts", "permalink", "photos", "videos", "reel"})

# Selector dos links que podem apontar para um post. Montado a partir de
# POST_PATH_KINDS para que o coletor e a leitura de data usem o mesmo conjunto:
# antes a data so era buscada em /posts/ e /videos/, entao posts em /permalink/,
# /photos/ ou /reel/ saiam com fonte_data vazia.
POST_LINK_SELECTOR = ", ".join(f'a[href*="/{kind}/"]' for kind in sorted(POST_PATH_KINDS))

# Filtro lexical que roda ANTES do LLM. O plano gratuito entrega 20
# classificacoes por dia, e um perfil de noticias da cidade publica noticia de
# servico, promocao e receita o dia inteiro. Sem esta porta de entrada, a cota
# do dia inteiro some em posts que o Gemini rejeitaria de qualquer jeito.
#
# Os termos sao os verbos de ocorrencia. Ficam de fora os que a taxonomia trata
# como contexto e nao fato: "iluminacao" e "area deserta" aparecem em texto
# institucional ("a iluminacao sera improveada"), e aceitar isso puxaria o LLM
# para classificar melhoria de obra como alerta.
TERMOS_OCORRENCIA = re.compile(
	r"\b("
	r"assalt\w*|roub\w*|furto|ladrao|arromb\w*|invadi\w*|"
	r"agress\w*|briga|violen\w*|ataque|espanc\w*|"
	r"assedi\w*|persegui\w*|ameaca\w*|"
	r"acidente|colis[aã]o|batida|capot\w*|"
	r"incendio|pegou fogo|"
	r"tiroteio|tir\w*|arma|armamento|"
	r"desaparecid\w*|morreu|morre\w*|v[ií]tima|"
	r"estupro|estuprador|"
	r"resgat\w*|socorro|emerg[eê]ncia|"
	r"embriaguez|bebida\s*alco[oó]lic\w*"
	r")\b",
	re.IGNORECASE,
)

# Quantos posts COLETAR por execucao. O gargalo real e a cota do Gemini, nao a
# coleta, mas o limite precisa ser folgado o bastante para produzir candidatos:
# o filtro lexical descarta cerca de 2/3 dos posts, entao ~50 coletados rendem
# algo proximo das 20 classificacoes diarias do plano gratuito.
PROBE_MAX_POSTS = 30
SCRAPE_MAX_POSTS = 50
# Meta do modo --collect. Nao consome cota (nao chama o LLM) e acumula entre
# execucoes, entao pode mirar volume alto: 1000 e a meta de acervo bruto.
COLLECT_MAX_POSTS = 1000
# Descobrir mais permalinks do que a meta cobre a taxa de falha de leitura
# (~30% em amostra: post de imagem/video sem mensagem longa devolve None).
COLLECT_DISCOVERY_FACTOR = 2

# Pausa entre chamadas ao LLM. O plano gratuito entrega 20 generate_content por
# DIA por modelo (GenerateRequestsPerDayPerProjectPerModel-FreeTier), e esse e
# o limite que de fato aperta; o limite por minuto (~15 RPM) folga com 5s.
CLASSIFY_PAUSE_SECONDS = 5.0

# Cota diaria observada no plano gratuito. Só aparece nesta linha para tornar
# visivel a ordem de grandeza quando o script interrompe por 429.
GEMINI_FREE_TIER_DAILY_REQUESTS = 20

# Rolagens para carregar o timeline. Facebook carrega por scroll, nao por paginacao.
SCROLL_STEP_PX = 3000
SCROLL_PAUSE_MS = 1500
# O coletor para quando atinge o max-posts ou quando SCROLL_ESTAGNACAO_PASSOS
# rolagens seguidas nao trazem post novo. O teto fixo de 12 rolagens que havia
# aqui nao alcancava o max-posts padrao, entao a coleta era subdimensionada.
SCROLL_MAX_PASSOS = 60
SCROLL_ESTAGNACAO_PASSOS = 5
# No modo --collect vale a pena rolar muito mais fundo: a descoberta rende ~2,4
# permalinks por rolagem (medido em 2026-10-13, ver SCRAPER.md), entao 1000 posts
# exigem centenas de rolagens. O corte real continua sendo a estagnacao.
COLLECT_SCROLL_MAX_PASSOS = 1500
# A leitura (uma navegacao por post) e o gargalo do --collect. Cada worker abre
# o proprio navegador e le em paralelo; 4 ja derruba ~1h para a casa dos minutos
# sem arrastar o Facebook a ponto de throttling.
READ_WORKERS_DEFAULT = 4
# Salva o acervo a cada N posts lidos. Uma rodada rumo a 1000 posts dura dezenas
# de minutos; sem isso, uma queda no fim desperdicaria todo o trabalho.
COLLECT_AUTOSAVE_A_CADA = 25
NAV_TIMEOUT_MS = 45000
SETUP_TIMEOUT_S = 300

USER_AGENT = (
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
	"(KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
)

# ---------------------------------------------------------------------------
# Utilitarios
# ---------------------------------------------------------------------------


def _load_dotenv() -> None:
	"""Le o .env sem sobrescrever variaveis ja definidas no ambiente.

	Procura em varios lugares porque o projeto nao padronizou um unico caminho:
	os populators leem o .env da raiz, e o scraper do Facebook usa scripts/.env.
	"""
	raiz = Path(__file__).resolve().parents[2]
	for env_path in (
		Path(__file__).resolve().parent / ".env",
		Path(__file__).resolve().parents[1] / ".env",
		raiz / ".env",
	):
		if not env_path.is_file():
			continue
		for line in env_path.read_text(encoding="utf-8-sig").splitlines():
			line = line.strip()
			if not line or line.startswith("#") or "=" not in line:
				continue
			key, _, value = line.partition("=")
			key = key.strip()
			value = value.strip().strip('"').strip("'")
			if key and value and key not in os.environ:
				os.environ[key] = value
		# Sem return: o primeiro arquivo tem prioridade por chave (o `not in
		# os.environ` acima), mas os seguintes ainda podem preencher chaves que
		# faltaram nele.


def _build_descricao(content: str, max_chars: int = 350) -> str:
	"""Junta frases ate atingir max_chars caracteres."""
	sentences = re.split(r"(?<=[.!?])\s+", content)
	descricao = ""
	for sentence in sentences:
		candidate = (descricao + " " + sentence).strip() if descricao else sentence
		if len(candidate) > max_chars and descricao:
			break
		descricao = candidate
		if len(descricao) >= max_chars:
			break
	return descricao.strip()


def _extract_address(content: str) -> str | None:
	"""Mesma estrategia do emboabas.py: procura logradouro ou bairro no texto."""
	patterns = [
		r"(?:na|no|ao)\s+(Rua|Avenida|Praça|Praca|Bairro|Rodovia|Estrada|BR[-\s]?\d+)[^,.;\n]{3,60}",
		r"(?:no bairro|no Bairro)\s+[A-ZÀ-Ü][^\n,.;:]{3,50}",
		r"(?:região|regiao)\s+d[oa]\s+[A-ZÀ-Ü][^\n,.;:]{3,40}",
	]
	for pattern in patterns:
		match = re.search(pattern, content, re.IGNORECASE)
		if match:
			found = re.sub(
				r"\s+(e|em|de|da|do|quando|onde)\s*$", "", match.group().strip(), flags=re.IGNORECASE
			)
			if len(found) <= 100:
				return found + ", São João del-Rei, MG"
	return None


def _normalize_permalink(href: str) -> str | None:
	"""Reduz o href do post a uma chave estavel, preservando o slug da pagina.

	O mesmo post aparece em formatos diferentes conforme a rolagem
	(?__cft__[], comment_id, ref) e as vezes como caminho relativo. Comparar o
	href cru geraria duplicata, mas o slug precisa sobreviver: sem ele a URL
	gravada em fonte_url deixa de abrir o post.

	Formas aceitas: /sjddoficial/posts/123 e /posts/123.
	"""
	if not href:
		return None
	href = href.split("?")[0].split("#")[0].rstrip("/")
	if not href:
		return None

	path = urlparse(href).path if "://" in href else href
	segments = [segment for segment in path.split("/") if segment]

	for index, segment in enumerate(segments):
		# index+1 existe = ha o id do post depois do tipo
		if segment in POST_PATH_KINDS and index + 1 < len(segments):
			return f"https://www.facebook.com/{'/'.join(segments[: index + 2])}"
	return None


def _load_seen() -> set[str]:
	"""Permalinks ja classificados em execucoes anteriores.

	Existe por causa do custo do LLM: reclassificar o historico inteiro a cada
	execucao seria pagar de novo por cada post antigo.
	"""
	if not SEEN_FILE.is_file():
		return set()
	try:
		return set(json.loads(SEEN_FILE.read_text(encoding="utf-8")))
	except (json.JSONDecodeError, OSError):
		return set()


def _save_seen(seen: set[str]) -> None:
	OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
	SEEN_FILE.write_text(json.dumps(sorted(seen), ensure_ascii=False, indent=2), encoding="utf-8")


def _load_collected() -> dict[str, dict]:
	"""Posts ja lidos pelo modo --collect, indexados pelo permalink.

	O acervo existe para acumular volume entre execucoes: ler o texto de um post
	e a parte lenta (uma navegacao por post), entao o que ja esta aqui nao e lido
	de novo na proxima rodada.
	"""
	if not POSTS_FILE.is_file():
		return {}
	try:
		posts = json.loads(POSTS_FILE.read_text(encoding="utf-8"))
	except (json.JSONDecodeError, OSError):
		return {}
	return {post["fonte_url"]: post for post in posts if post.get("fonte_url")}


def _save_collected(coletados: dict[str, dict]) -> None:
	"""Grava o acervo de forma atomica.

	A gravacao direta sobre o arquivo final e uma janela de risco: uma queda no
	meio do write deixa um JSON truncado e o acervo inteiro se perde. Escrever
	num temporario e trocar com os.replace elimina a janela (replace e atomico no
	mesmo volume), o que importa agora que o acervo e salvo durante a rodada.
	"""
	OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
	conteudo = json.dumps(list(coletados.values()), ensure_ascii=False, indent=2)
	temporario = POSTS_FILE.with_suffix(".json.tmp")
	temporario.write_text(conteudo, encoding="utf-8")
	os.replace(temporario, POSTS_FILE)


# ---------------------------------------------------------------------------
# Navegacao
# ---------------------------------------------------------------------------


def _open_context(playwright, headless: bool):
	"""Abre o Chromium com o perfil autenticado."""
	PROFILE_DIR.mkdir(parents=True, exist_ok=True)
	context = playwright.chromium.launch_persistent_context(
		user_data_dir=str(PROFILE_DIR),
		headless=headless,
		user_agent=USER_AGENT,
		locale="pt-BR",
		timezone_id="America/Sao_Paulo",
		viewport={"width": 1366, "height": 900},
		# remove a marca de automacao que o Playwright injeta por padrao
		args=["--disable-blink-features=AutomationControlled"],
	)
	context.set_default_timeout(NAV_TIMEOUT_MS)
	return context


def _new_reading_context(playwright, headless: bool, storage_state: dict):
	"""Abre um Chromium descartavel autenticado pelo storage_state exportado.

	A leitura paralela nao pode reusar o perfil persistente: um user_data_dir so
	aceita um contexto por vez, e a API sync do Playwright nao atravessa threads.
	Entao cada worker abre o proprio navegador e injeta os cookies exportados do
	perfil ja autenticado (a sessao sobreviveu ao storage_state no teste).
	"""
	browser = playwright.chromium.launch(
		headless=headless,
		args=["--disable-blink-features=AutomationControlled"],
	)
	context = browser.new_context(
		storage_state=storage_state,
		user_agent=USER_AGENT,
		locale="pt-BR",
		timezone_id="America/Sao_Paulo",
		viewport={"width": 1366, "height": 900},
	)
	context.set_default_timeout(NAV_TIMEOUT_MS)
	return browser, context


def _run_setup(playwright) -> None:
	"""Abre o navegador visivel para o usuario fazer login uma unica vez."""
	print("[facebook] Abrindo o Chromium para o login manual...")
	print("[facebook] Faça login normalmente e espere a pagina carregar.")
	print(f"[facebook] O perfil fica em: {PROFILE_DIR}")
	print("[facebook] Se o login pedir confirmacao de identidade, faca manualmente.")

	context = _open_context(playwright, headless=False)
	try:
		page = context.new_page()
		page.goto("https://www.facebook.com/login", wait_until="domcontentloaded")
		page.wait_for_timeout(SETUP_TIMEOUT_S * 1000)
	finally:
		context.close()

	print("[facebook] Sessao salva. Rode `--probe` para conferir o que a pagina publica.")


def _assert_session_alive(page) -> None:
	"""Falha alto quando a sessao morreu.

	Este e o ponto mais caro do script se falhar em silencio: uma sessao
	expirada devolve zero posts, e zero posts parece uma pagina que nao
	publicou nada novo.
	"""
	if "/login" in page.url or "/checkpoint" in page.url:
		raise RuntimeError(
			"Sessao do Facebook expirada ou invalida (a URL virou tela de login). "
			"Rode novamente: py scripts\\scrapers\\facebook_sjddoficial.py --setup"
		)
	if page.query_selector('input[type="password"]'):
		raise RuntimeError(
			"O Facebook esta pedindo login. Rode --setup para renovar a sessao."
		)


# O Facebook insere o COMBINING GRAPHEME JOINER (U+034F) entre letras de alguns
# blocos, embaralhando o texto para atrapalhar leitura automatica. O conteudo
# muda a cada renderizacao, entao nunca e a mensagem do post: e ruido.
MARCA_OFUSCACAO = "\u034f"

RUIDO_DO_POST = (
	"Privacidade",
	"Termos",
	"Publicidade",
	"Escolhas para anúncios",
	"Escolhas para anuncios",
	"Cookies",
	"Na próxima vez que fizer login",
	"Political",
	"Anuncie",
)

RELATIVO_RE = re.compile(
	r"^(?:agora|ontem|hoje|"
	r"(?P<n>\d+)\s*(?P<u>min|minutos?|h|hr|horas?|d|dias?|sem|semanas?))\s*$",
	re.IGNORECASE,
)


def _resolve_post_data(texto: str) -> str:
	"""Converte o rotulo relativo do Facebook ("7 min", "3 h") em data ISO.

	A pagina nao expoe timestamp absoluto: nem <abbr> nem data-* existem nesse
	layout. O unico sinal e o rotulo relativo do link do post, que e ancorado
	no instante da leitura. Perder a data por completo era pior do que guarda-la
	com resolucao de minuto, entao o rotulo vira datetime relativo a agora.
	"""
	texto = (texto or "").strip()
	if not texto:
		return ""

	match = RELATIVO_RE.match(texto)
	if not match:
		return ""

	agora = datetime.now(timezone.utc)
	if texto.lower() in ("agora", "hoje"):
		return agora.isoformat()
	if texto.lower() == "ontem":
		return (agora - timedelta(days=1)).isoformat()

	quantidade = int(match.group("n"))
	unidade = match.group("u").lower()
	if unidade.startswith("min"):
		delta = timedelta(minutes=quantidade)
	elif unidade.startswith(("h", "hr", "hora")):
		delta = timedelta(hours=quantidade)
	elif unidade.startswith("d"):
		delta = timedelta(days=quantidade)
	else:
		delta = timedelta(weeks=quantidade)

	return (agora - delta).isoformat()


def _collect_post_ids(
	page, page_url: str, max_posts: int, max_passos: int | None = None
) -> list[str]:
	"""Lista os permalinks de post que aparecem na pagina do perfil.

	A pagina do perfil nao expoe os posts: o que role=article traz sao
	comentarios. Ainda assim cada comentario carrega o permalink do post ao
	qual pertence, entao os ids sao montados a partir desses hrefs. Por isso o
	rendimento e limitado ao numero de comentarios visiveis na rolagem.

	Limitacao conhecida e testada (2026-09-29): o perfil publica um feed
	"assistente" em /sjddoficial/supporters, cujo conteudo so aparece para
	assinantes. O grupo /groups/sjdd responde "conteudo nao disponivel". Nao ha
	feed alternativo que exponha os posts sem comentario, e as abas /posts/ e
	?sk=list redirecionam de volta para a pagina inicial. Portanto a cobertura
	deste coletor e enviesada: ela enxerga apenas posts que receberam
	comentario. Ampliar exige outra fonte, nao mais rolagem.

	`max_passos` permite rolar mais fundo que o padrao (usado pelo modo
	--collect para mirar volume alto). O corte real continua sendo a estagnacao.
	"""
	page.goto(page_url, wait_until="domcontentloaded")
	_assert_session_alive(page)
	page.wait_for_timeout(SCROLL_PAUSE_MS * 2)

	permalinks: list[str] = []
	seen: set[str] = set()
	rolagens_sem_novidade = 0

	for _ in range(max_passos or SCROLL_MAX_PASSOS):
		antes = len(permalinks)
		hrefs = page.eval_on_selector_all(
			POST_LINK_SELECTOR,
			"els => els.map(el => el.getAttribute('href') || '')",
		)
		for href in hrefs:
			permalink = _normalize_permalink(href)
			if permalink and permalink not in seen:
				seen.add(permalink)
				permalinks.append(permalink)

		if len(permalinks) >= max_posts:
			break
		rolagens_sem_novidade = rolagens_sem_novidade + 1 if len(permalinks) == antes else 0
		if rolagens_sem_novidade >= SCROLL_ESTAGNACAO_PASSOS:
			break
		page.mouse.wheel(0, SCROLL_STEP_PX)
		page.wait_for_timeout(SCROLL_PAUSE_MS)

	return permalinks[:max_posts]


def _read_post(page, permalink: str) -> dict | None:
	"""Abre o permalink e le a mensagem e a data do post.

	Na pagina do post a mensagem e o primeiro bloco [dir=auto] longo e fora do
	rodape. Ordem do DOM vence tamanho: um comentario longo pode ser maior que
	a mensagem, mas sempre aparece depois dela.
	"""
	page.goto(permalink, wait_until="domcontentloaded")
	page.wait_for_timeout(SCROLL_PAUSE_MS * 2)

	blocos = page.eval_on_selector_all(
		'[dir="auto"]',
		"els => els.map(el => (el.innerText || '').trim())",
	)

	mensagem = ""
	for texto in blocos:
		if len(texto) < 90:
			continue
		if MARCA_OFUSCACAO in texto:
			continue
		if any(ruido in texto for ruido in RUIDO_DO_POST):
			continue
		mensagem = texto
		break
	if not mensagem:
		return None

	stamps = page.eval_on_selector_all(
		POST_LINK_SELECTOR,
		"els => els.map(el => ({href: el.getAttribute('href') || '', txt: (el.innerText || '').trim()}))",
	)
	fonte_data = ""
	for stamp in stamps:
		if _normalize_permalink(stamp["href"]) != permalink:
			continue
		fonte_data = _resolve_post_data(stamp["txt"])
		if fonte_data:
			break

	return {
		"titulo": _build_descricao(mensagem, max_chars=120),
		"conteudo_completo": mensagem,
		"fonte_url": permalink,
		"fonte_data": fonte_data,
	}


def _read_posts_parallel(
	permalinks: list[str],
	storage_state: dict,
	headless: bool,
	alvo: int,
	coletados: dict[str, dict],
	workers: int,
) -> None:
	"""Le os permalinks em paralelo, cada worker no proprio navegador.

	Paraleliza o gargalo real (uma navegacao por post) sem tocar na descoberta,
	que continua sequencial no perfil persistente. Os workers puxam o proximo
	permalink da fila comum e param assim que o acervo atinge a meta; tanto a
	fila quanto o dicionario de resultados sao protegidos por um lock.
	"""
	from concurrent.futures import ThreadPoolExecutor

	from playwright.sync_api import sync_playwright

	travas = threading.Lock()
	total = len(permalinks)
	estado = {"proximo": 0, "lidos": 0, "falhas": 0}

	def trabalhador() -> None:
		with sync_playwright() as playwright:
			browser, context = _new_reading_context(playwright, headless, storage_state)
			try:
				page = context.new_page()
				while True:
					with travas:
						if len(coletados) >= alvo or estado["proximo"] >= total:
							return
						permalink = permalinks[estado["proximo"]]
						estado["proximo"] += 1
					try:
						post = _read_post(page, permalink)
					except Exception:  # um post ruim nao pode derrubar a rodada inteira
						post = None
					with travas:
						if post:
							coletados[permalink] = post
							estado["lidos"] += 1
						else:
							estado["falhas"] += 1
						feitos = estado["lidos"] + estado["falhas"]
						print(
							f"[facebook] Lendo {feitos}/{total} "
							f"({estado['lidos']} ok, {estado['falhas']} sem texto)   ",
							end="\r",
							flush=True,
						)
						if post and estado["lidos"] % COLLECT_AUTOSAVE_A_CADA == 0:
							_save_collected(coletados)
			finally:
				browser.close()

	with ThreadPoolExecutor(max_workers=workers) as pool:
		for _ in range(workers):
			pool.submit(trabalhador)
	print(" " * 64, end="\r")


def _collect_articles(page, page_url: str, max_posts: int) -> list[dict]:
	"""Descobre permalinks na pagina do perfil e le cada post.

	Sao duas etapas porque o perfil entrega ids e o post entrega o texto: no
	perfil o texto visivel e o do comentario, nao o da ocorrencia.
	"""
	permalinks = _collect_post_ids(page, page_url, max_posts)
	if not permalinks:
		return []

	posts: list[dict] = []
	for permalink in permalinks:
		if len(posts) >= max_posts:
			break
		post = _read_post(page, permalink)
		if post:
			posts.append(post)
	return posts


# ---------------------------------------------------------------------------
# Classificacao (Gemini)
# ---------------------------------------------------------------------------


def _build_schema():
	from google.genai import types

	return types.Schema(
		type=types.Type.OBJECT,
		properties={
			"relevante": types.Schema(
				type=types.Type.BOOLEAN,
				description="True se o post descreve um perigo ou ocorrencia de seguranca publica no territorio de Sao Joao del-Rei.",
			),
			"tipo_perigo": types.Schema(
				type=types.Type.STRING,
				enum=list(TIPO_PERIGO_VALUES),
				description="Categoria do alerta. String vazia quando relevante for False.",
			),
			"confianca": types.Schema(
				type=types.Type.NUMBER,
				description="Confianca de 0 a 1 sobre a classificacao e a localizacao.",
			),
			"endereco": types.Schema(
				type=types.Type.STRING,
				description="Logradouro ou bairro citado, com cidade e estado. String vazia se nao houver.",
			),
			"justificativa": types.Schema(
				type=types.Type.STRING,
				description="Uma frase explicando a decisao. Serve para auditoria manual.",
			),
		},
		required=["relevante", "tipo_perigo", "confianca", "endereco", "justificativa"],
	)


def _aplicar_filtro_lexical(posts: list[dict]) -> tuple[list[dict], list[dict]]:
	"""Separa os posts que tem chance de virar alerta. Nao chama o LLM.

	A cota do plano gratuito e de 20 classificacoes por dia, e o perfil publica
	noticia de servico, promocao e receita o dia inteiro. Deixar o Gemini
	responder a tudo gasta a cota inteira em posts que ele rejeitaria, e nao ha
	como recuperar: o dia ja foi. E um filtro de palavra-chave e conservador por
	desenho — ele so descarta quem nao tem NENHUM termo de ocorrencia, e quem
	passa ainda pode ser rejeitado pelo LLM depois.

	Retorna (candidatos, barrados), preservando a ordem de coleta.
	"""
	candidatos: list[dict] = []
	barrados: list[dict] = []
	for post in posts:
		alvo = f"{post.get('titulo', '')}\n{post.get('conteudo_completo', '')}"
		(candidatos if TERMOS_OCORRENCIA.search(alvo) else barrados).append(post)
	return candidatos, barrados


def _build_prompt(page_url: str) -> str:
	categorias = "\n".join(f"- {valor}" for valor in TIPO_PERIGO_VALUES)
	return f"""Voce classifica posts de uma pagina oficial de prefeitura para decidir
se cada um vira um alerta de seguranca em um aplicativo de protecao cidada.

Fonte: {page_url}

Responda com JSON puro, respeitando o schema fornecido.

Marque relevante=true APENAS quando o post:
- descreve um perigo concreto ja ocorrido ou em andamento (crime, acidente,
  incendio, bloqueio de via, area deserta, ameaca a pessoa);
- E ocorre em Sao Joao del-Rei ou nos municipios vizinhos (Barra do Pira,
  Mar de Espanha, Santo Antonio do Amparo, Resende, Conceicao do Rio,
  Ibertioga, Nazarene, Santa Cruz do Rio Pardo).

Marque relevante=false para tudo que nao ameaca a pessoa: aviso de obra,
programacao cultural, data comemorativa, comunicado administrativo,
suspensao de servico sem risco, folder institucional, divulgacao de
programacao, e aviso de neblina ou de chuva com o trafego fluindo normalmente.

Quando relevante=false, tipo_perigo e endereco devem ser string vazia.

Categorias permitidas para tipo_perigo:
{categorias}

Se o post for relevante mas nao citar logradouro, use o bairro ou a referencia
geografica citada no texto (ex: "Centro, Sao Joao del-Rei, MG"). Nunca invente
logradouro que nao aparece no texto.

A confianca e o seu grau de certeza sobre os dois juzos juntos: ser relevante
E estar em Sao Joao del-Rei. Um post sobre perigo real em outra cidade do
estado tem confianca baixa.
"""


DIARIA_QUOTA_METRIC = "PerDayPerProjectPerModel"


def _cota_diaria_esgotada(exc) -> bool:
	"""Diz se o 429 e cota diaria, e nao estouro de taxa por minuto.

	O plano gratuito entrega 20 generate_content por dia por modelo
	(GenerateRequestsPerDayPerProjectPerModel-FreeTier). Quando ela acaba, o
	RetryInfo que a API devolve sugere 3s a 48s, o que e mentira: a cota so volta
	no dia seguinte. Inserir nesse caminho o retry do dia seguinte e o que
	permite ao script falhar rapido e devolver o controle, em vez de queimar
	quatro chamadas por post contra um limite que nao muda em minutos.

	O unico sinal confiavel e o nome da metrica diaria. Um 429 de RPM tambem
	traz a frase "quota exceeded", entao casar so a frase abortaria a execucao
	inteira por um limite que se recupera em segundos.
	"""
	return DIARIA_QUOTA_METRIC in str(exc)


def _generate(client, model, config, body: str, retries: int = 4) -> dict:
	"""Chama o Gemini com retry em erro transitorio.

	A API responde 503 sob demanda alta e 429 quando o limite de taxa da conta
	estoura. Sem retry, uma rajada apagaria o post sem que o operador percebesse.
	O backoff e exponencial porque 429 exige esperar de verdade. Cota diaria
	excedida e o unico caso em que insistir e perda: ela nao se recupera em
	minutos, entao o erro sobe na hora.
	"""
	from google.genai import errors

	ultimo: Exception | None = None
	for tentativa in range(retries):
		try:
			response = client.models.generate_content(model=model, contents=body, config=config)
			return json.loads(response.text)
		except (errors.ServerError, errors.ClientError) as exc:
			ultimo = exc
			code = getattr(exc, "code", None)
			if code == 429 and _cota_diaria_esgotada(exc):
				raise CotaDiariaEsgotada(
					"Cota diaria do Gemini esgotada (20 requisicoes/dia no plano gratuito). "
					"O post nao foi classificado e sera retentado amanha."
				) from exc
			# So o 429 de taxa por minuto vale nova tentativa: ele se recupera em
			# segundos. O 503 (modelo sobrecarregado) tambem consome a cota diaria
			# a cada tentativa no plano gratuito, entao insistir nele queima o
			# pouco do dia. Melhor desistir deste post agora: ele nao entra no
			# seen e volta inteiro na proxima execucao.
			if code != 429 or tentativa == retries - 1:
				break
			espera = 3 * 2 ** tentativa
			print(f"\n[facebook] Limite de taxa (HTTP 429), nova tentativa em {espera}s...")
			time.sleep(espera)
		except json.JSONDecodeError as exc:
			raise RuntimeError(f"O Gemini devolveu resposta que nao e JSON valido: {exc}") from exc
	raise RuntimeError(f"Falha ao consultar o Gemini apos {retries} tentativa(s): {ultimo}")


def _classify_all(posts: list[dict], page_url: str) -> tuple[list[dict], set[str], bool]:
	"""Classifica cada post. Retorna (relevantes, processados, cota_esgotada).

	`processados` sao os permalinks que o Gemini respondeu de fato. Quem falhou
	NAO entra no .fb_seen.json e assim sera retentado na proxima execucao.
	"""
	from google import genai
	from google.genai import types

	api_key = os.environ.get("GEMINI_API_KEY", "").strip()
	if not api_key:
		raise RuntimeError(
			"GEMINI_API_KEY nao encontrada. Copie scripts\\scrapers\\.env.example "
			"para scripts\\.env e preencha a chave."
		)

	client = genai.Client(api_key=api_key)
	schema = _build_schema()
	# Sem temperature: no Gemini 3.6+ ela e aceita e ignorada, e geracoes
	# futuras rejeitam com HTTP 400. O determinismo aqui vem do response_schema.
	config = types.GenerateContentConfig(
		response_mime_type="application/json",
		response_schema=schema,
		# Nao usamos ferramentas (function calling); desligar o AFC tira o aviso
		# "Direct use of automatic function calling..." e o loop extra do SDK.
		automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
	)
	prompt = _build_prompt(page_url)

	resultados: list[dict] = []
	processados: set[str] = set()
	cota_esgotada = False

	for index, post in enumerate(posts, start=1):
		print(f"[facebook] Classificando {index}/{len(posts)}...", end="\r", flush=True)
		body = f"{prompt}\n\ntitulo: {post['titulo']}\n\ntexto: {post['conteudo_completo'][:4000]}"
		try:
			veredito = _generate(client, GEMINI_MODEL, config, body)
		except CotaDiariaEsgotada as exc:
			# A cota nao volta dentro desta execucao. Gastar o resto da fila
			# aqui so produziria a mesma resposta de erro N vezes.
			cota_esgotada = True
			restantes = len(posts) - index + 1
			print(f"\n[facebook] {exc}")
			print(f"[facebook] Interrompido: {restantes} post(s) ficaram sem classificacao e voltam na proxima execucao.")
			break
		except RuntimeError as exc:
			print(f"\n[facebook] Descartado por falha de API: '{post['titulo'][:60]}' ({exc})")
			continue

		processados.add(post["fonte_url"])

		# A pausa vale para TODA chamada bem-sucedida ao LLM, nao so para as
		# aprovadas: o RPM conta requisicoes, e o post rejeitado tambem gastou
		# uma. Antes ela ficava depois do `continue` abaixo, entao a maioria
		# dos posts (rejeitados) escapava da pausa e disparava em rajada.
		time.sleep(CLASSIFY_PAUSE_SECONDS)

		if not veredito.get("relevante"):
			continue

		tipo = veredito.get("tipo_perigo", "")
		if tipo not in TIPO_PERIGO_VALUES:
			print(f"\n[facebook] Descartado: '{post['titulo'][:60]}' retornou tipo '{tipo}' fora do enum.")
			continue

		conteudo = post["conteudo_completo"]
		resultados.append({
			"titulo": post["titulo"],
			"descricao": _build_descricao(conteudo),
			"conteudo_completo": conteudo,
			"endereco": veredito.get("endereco") or _extract_address(conteudo),
			"tipo_perigo": tipo,
			"confianca": veredito.get("confianca"),
			"justificativa": veredito.get("justificativa", ""),
			"fonte_url": post["fonte_url"],
			"fonte_data": post["fonte_data"],
		})

	print(" " * 40, end="\r")
	return resultados, processados, cota_esgotada


# ---------------------------------------------------------------------------
# Modos
# ---------------------------------------------------------------------------


def _load_page_url() -> str:
	return os.environ.get("FB_PAGE_URL", "").strip() or DEFAULT_PAGE_URL


def run_probe(playwright, headless: bool, max_posts: int) -> None:
	"""Reconhecimento: extrai titulos sem chamar o LLM."""
	page_url = _load_page_url()
	print(f"[facebook] Sondando {page_url} (limite de {max_posts} posts)...")

	context = _open_context(playwright, headless=headless)
	try:
		page = context.new_page()
		posts = _collect_articles(page, page_url, max_posts)
	finally:
		context.close()

	if not posts:
		print("[facebook] Nenhum post encontrado.")
		print("[facebook] Se a pagina abre no seu navegador, provavelmente a sessao expirou: rode --setup.")
		return

	candidatos, barrados = _aplicar_filtro_lexical(posts)

	OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
	PROBE_FILE.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")

	print(f"\n[facebook] {len(posts)} posts coletados, {len(candidatos)} passaram no filtro lexical:")
	for post in candidatos:
		print(f"  - {post['titulo'][:100]}")
	if barrados:
		print(f"\n[facebook] {len(barrados)} barrados sem chamar o LLM (o filtro nao chama e nao gasta cota):")
		for post in barrados:
			print(f"  x {post['titulo'][:92]}")
	print(f"\n[facebook] Salvo em: {PROBE_FILE}")


def run_collect(playwright, headless: bool, max_posts: int, workers: int) -> None:
	"""Coleta posts para o acervo SEM classificar. Nao gasta cota do LLM.

	Diferente de --probe (que so amostra) e de --scrape (que classifica e
	consome cota), este modo persegue volume: rola o feed o quanto der e le o
	texto dos posts que ainda nao estao no acervo. O resultado fica em
	facebook_sjddoficial_posts.json e e acumulativo: rodar de novo so paga pela
	leitura do que e novo, entao a meta (padrao COLLECT_MAX_POSTS) pode ser
	alcancada em varias execucoes.

	A descoberta continua sequencial (perfil persistente); so a leitura roda em
	paralelo, com `workers` navegadores independentes autenticados pelo
	storage_state exportado.
	"""
	page_url = _load_page_url()
	print(f"[facebook] Coletando {page_url} para o acervo (meta {max_posts} posts, sem classificar)...")

	coletados = _load_collected()
	print(f"[facebook] {len(coletados)} posts ja no acervo.")

	context = _open_context(playwright, headless=headless)
	try:
		page = context.new_page()
		# Descobrir mais do que a meta porque nem todo permalink rende texto: o
		# _read_post devolve None em posts sem mensagem longa (imagem/video puro),
		# e sem essa folga o acervo pararia abaixo de max_posts.
		permalinks = _collect_post_ids(
			page, page_url, max_posts * COLLECT_DISCOVERY_FACTOR, max_passos=COLLECT_SCROLL_MAX_PASSOS
		)
		print(f"[facebook] {len(permalinks)} permalinks descobertos no feed.")
		# Exportado antes de fechar o perfil: os workers reabrem a sessao a partir
		# dos cookies, sem disputar o user_data_dir (que so aceita um contexto).
		storage_state = context.storage_state()
	finally:
		context.close()

	novos = [permalink for permalink in permalinks if permalink not in coletados]
	if len(coletados) >= max_posts:
		print(f"[facebook] Meta de {max_posts} posts ja atingida; nada a ler.")
	elif novos:
		print(f"[facebook] {len(novos)} ainda nao lidos; lendo com {workers} workers...")
		_read_posts_parallel(novos, storage_state, headless, max_posts, coletados, workers)

	_save_collected(coletados)

	total = len(coletados)
	print(f"[facebook] Acervo com {total} posts ({POSTS_FILE}).")
	if total < max_posts:
		print(f"[facebook] Faltam {max_posts - total} para a meta; rode de novo para acumular.")
	else:
		print("[facebook] Meta de acervo atingida.")


def run_classify(max_posts: int | None) -> None:
	"""Classifica o acervo do --collect, sem raspar de novo nem abrir navegador.

	O texto ja esta em POSTS_FILE, entao o unico custo e a cota do LLM (20/dia).
	Roda ao longo dos dias para consumir o acervo aos poucos; o .fb_seen.json
	garante que um post ja respondido nunca seja reclassificado. `max_posts`
	limita quantos candidatos vao ao LLM nesta rodada (util para nao iniciar uma
	fila maior do que a cota aguenta); sem ele, vai ate a cota acabar.
	"""
	page_url = _load_page_url()
	coletados = _load_collected()
	if not coletados:
		print("[facebook] Acervo vazio. Rode --collect primeiro para juntar posts.")
		return

	seen = _load_seen()
	novos = [post for post in coletados.values() if post["fonte_url"] not in seen]
	print(f"[facebook] Acervo com {len(coletados)} posts; {len(novos)} ainda nao classificados.")
	if not novos:
		print("[facebook] Nada novo para classificar.")
		return

	candidatos, barrados = _aplicar_filtro_lexical(novos)
	print(f"[facebook] Filtro lexical: {len(candidatos)} candidatos, {len(barrados)} barrados.")

	if max_posts:
		candidatos = candidatos[:max_posts]
		print(f"[facebook] Limitando a {len(candidatos)} candidatos nesta rodada (--max-posts).")

	if not candidatos:
		print("[facebook] Nenhum candidato passou no filtro lexical; nada a enviar ao Gemini.")
		_save_seen(seen | {post["fonte_url"] for post in barrados})
		return

	relevantes, processados, cota_esgotada = _classify_all(candidatos, page_url)
	print(f"\n[facebook] {len(relevantes)} de {len(candidatos)} candidatos relevantes como alerta.")

	falhas = len(candidatos) - len(processados)
	if falhas:
		quando = "amanha" if cota_esgotada else "na proxima execucao"
		print(f"[facebook] {falhas} candidatos nao foram classificados e serao retentados {quando}.")

	# Mesma regra do run_scrape: o que o Gemini respondeu entra no seen sempre
	# (inclusive se a cota acabou no meio), e o barrado por palavra-chave so
	# entra quando a classificacao terminou inteira.
	vistos = seen | processados
	if barrados and not cota_esgotada:
		vistos |= {post["fonte_url"] for post in barrados}

	OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
	anteriores = json.loads(OUTPUT_FILE.read_text(encoding="utf-8")) if OUTPUT_FILE.is_file() else []
	por_url = {item["fonte_url"]: item for item in [*anteriores, *relevantes]}
	OUTPUT_FILE.write_text(
		json.dumps(list(por_url.values()), ensure_ascii=False, indent=2), encoding="utf-8"
	)
	_save_seen(vistos)

	print(f"[facebook] Relatorios salvos em: {OUTPUT_FILE}")
	if cota_esgotada:
		print("[facebook] Cota do dia esgotada; rode de novo amanha para continuar.")


def run_scrape(playwright, headless: bool, max_posts: int, dry_run: bool) -> None:
	page_url = _load_page_url()
	mode = "dry-run" if dry_run else "scrape"
	print(f"[facebook] Coletando {page_url} (limite de {max_posts} posts)...")

	context = _open_context(playwright, headless=headless)
	try:
		page = context.new_page()
		posts = _collect_articles(page, page_url, max_posts)
	finally:
		context.close()

	if not posts:
		print("[facebook] Nenhum post encontrado. Se a pagina abre no seu navegador, a sessao expirou: rode --setup.")
		return

	seen = _load_seen()
	novos = [post for post in posts if post["fonte_url"] not in seen]
	print(f"[facebook] {len(posts)} posts no timeline, {len(novos)} ainda nao classificados.")

	if not novos:
		print("[facebook] Nada novo desde a ultima execucao.")
		return

	# O filtro roda antes do LLM, mas DEPOIS do seen: assim um barrado hoje
	# continua sendo reavaliado amanha caso o perfil edite o texto, e a cota so
	# e gasta em quem realmente merece consulta.
	candidatos, barrados = _aplicar_filtro_lexical(novos)
	if barrados:
		print(f"[facebook] Filtro lexical: {len(barrados)} barrados sem chamar o LLM.")
		if dry_run:
			for post in barrados:
				print(f"    x {post['titulo'][:92]}")

	if not candidatos:
		print(f"[facebook] Nenhum dos {len(novos)} posts passou no filtro lexical.")
		print("[facebook] Nada a enviar ao Gemini hoje, e nada foi gravado.")
		if not dry_run:
			# Sem candidato nao existe motivo para reprocessar isto mais tarde,
			# entao o que ja foi visto pode ser gravado sem risco.
			_save_seen(seen | {post["fonte_url"] for post in barrados})
		return

	relevantes, processados, cota_esgotada = _classify_all(candidatos, page_url)
	print(f"\n[facebook] {len(relevantes)} de {len(candidatos)} candidatos relevantes como alerta.")

	falhas = len(candidatos) - len(processados)
	if falhas:
		quando = "amanha" if cota_esgotada else "na proxima execucao"
		print(f"[facebook] {falhas} candidatos nao foram classificados e serao retentados {quando}.")
	# O que o Gemini ja respondeu entra no seen SEMPRE, inclusive quando a cota
	# acabou no meio da fila: esses posts ja foram classificados (pagos) e
	# reclassifica-los amanha gastaria de novo a cota do dia seguinte.
	# O barrado por palavra-chave so entra quando nao houve cota esgotada: o
	# filtro e barato e deterministico, mas so pode ser considerado definitivo
	# para a rodada quando a classificacao terminou inteira.
	vistos = seen | processados
	if barrados and not cota_esgotada:
		vistos |= {post["fonte_url"] for post in barrados}

	if dry_run:
		print("[facebook] dry-run: nada foi gravado.\n")
		for item in relevantes:
			print(f"  [{item['tipo_perigo']}] confianca={item['confianca']} {item['titulo'][:80]}")
			print(f"      {item['justificativa']}")
		return

	OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
	anteriores = json.loads(OUTPUT_FILE.read_text(encoding="utf-8")) if OUTPUT_FILE.is_file() else []
	combinado = anteriores + relevantes
	por_url = {item["fonte_url"]: item for item in combinado}

	OUTPUT_FILE.write_text(
		json.dumps(list(por_url.values()), ensure_ascii=False, indent=2), encoding="utf-8"
	)
	_save_seen(vistos)

	print(f"[facebook] Salvo em: {OUTPUT_FILE}")


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Coleta posts da pagina do municipio no Facebook e classifica por LLM."
	)
	modo = parser.add_mutually_exclusive_group(required=True)
	modo.add_argument("--setup", action="store_true", help="abre o navegador para login manual (uma vez)")
	modo.add_argument("--probe", action="store_true", help="lista os posts sem chamar o LLM")
	modo.add_argument(
		"--collect", action="store_true", help="acumula posts no acervo sem classificar (nao gasta cota)"
	)
	modo.add_argument(
		"--classify", action="store_true", help="classifica o acervo (--collect) sem raspar de novo"
	)
	modo.add_argument("--scrape", action="store_true", help="coleta e classifica")
	modo.add_argument(
		"--dry-run", action="store_true", help="como --scrape, mas imprime sem gravar"
	)
	parser.add_argument(
		"--max-posts", type=int, default=None, help=f"limite de posts (padrao {PROBE_MAX_POSTS} no probe, {COLLECT_MAX_POSTS} no collect, {SCRAPE_MAX_POSTS} no scrape)"
	)
	parser.add_argument(
		"--workers",
		type=int,
		default=READ_WORKERS_DEFAULT,
		help=f"navegadores paralelos no --collect (padrao {READ_WORKERS_DEFAULT})",
	)
	parser.add_argument(
		"--headed", action="store_true", help="abre o navegador visivel (para depurar)"
	)
	return parser.parse_args()


def main() -> None:
	args = _parse_args()
	_load_dotenv()

	if args.classify:
		# Nao usa navegador: classifica o texto ja salvo pelo --collect.
		run_classify(args.max_posts)
		return

	try:
		from playwright.sync_api import sync_playwright
	except ImportError as exc:
		raise SystemExit(
			"Playwright nao encontrado. Instale com:\n"
			"  python -m venv scripts\\.venv\n"
			"  scripts\\.venv\\Scripts\\python -m pip install -r scripts\\scrapers\\requirements.txt\n"
			"  scripts\\.venv\\Scripts\\python -m playwright install chromium"
		) from exc

	headless = not (args.headed or args.setup)

	with sync_playwright() as playwright:
		if args.setup:
			_run_setup(playwright)
		elif args.probe:
			run_probe(playwright, headless, args.max_posts or PROBE_MAX_POSTS)
		elif args.collect:
			run_collect(playwright, headless, args.max_posts or COLLECT_MAX_POSTS, args.workers)
		else:
			run_scrape(playwright, headless, args.max_posts or SCRAPE_MAX_POSTS, args.dry_run)


if __name__ == "__main__":
	try:
		main()
	except KeyboardInterrupt:
		print("\n[facebook] Interrompido.")
		sys.exit(130)
	except RuntimeError as exc:
		print(f"\n[facebook] Erro: {exc}")
		sys.exit(1)
