"""Scraper do portal G1 (Zona da Mata) focado em São João del Rei.

Fonte: https://g1.globo.com/mg/zona-da-mata/
Metodo: RSS Feed do G1 filtrado por localidade (apenas stdlib)

Execucao:
    py scripts\\scrapers\\g1_sao_joao_del_rei.py

Saida:
    scripts\\data\\g1_sao_joao_del_rei_reports.json
"""

import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# ---------------------------------------------------------------------------
# Configuracao
# ---------------------------------------------------------------------------

RSS_URL = "https://g1.globo.com/rss/g1/mg/zona-da-mata/"
USER_AGENT = "vigIA-scraper/1.0 (desenvolvimento local)"

# Diretorio de saida
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data"
OUTPUT_FILE = OUTPUT_DIR / "g1_sao_joao_del_rei_reports.json"


def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()

def _extract_address(content: str) -> str | None:
    patterns = [
        r"(?:na|no|ao)\s+(Rua|Avenida|Praça|Praca|Bairro|Rodovia|Estrada|BR[-\s]?\d+)[^,.;\n]{3,60}"
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            found = match.group().strip()
            found = re.sub(r"\s+(e|em|de|da|do|quando|onde)\s*$", "", found, flags=re.IGNORECASE)
            if len(found) <= 100:
                return found + ", São João del Rei, MG"
    return "São João del Rei, MG"

def scrape() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("[g1] Buscando feed RSS da Zona da Mata...")
    try:
        req = Request(RSS_URL, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=20) as response:
            xml_data = response.read()
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"Falha na comunicacao com o G1: {exc}") from exc
        
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as exc:
        raise RuntimeError(f"Falha ao processar o XML do feed: {exc}") from exc

    all_entries = []
    items = root.findall(".//item")
    print(f"  {len(items)} noticias encontradas no feed geral.")

    for item in items:
        title_elem = item.find("title")
        link_elem = item.find("link")
        desc_elem = item.find("description")
        date_elem = item.find("pubDate")
        
        title = title_elem.text if title_elem is not None else ""
        link = link_elem.text if link_elem is not None else ""
        desc_html = desc_elem.text if desc_elem is not None else ""
        pub_date = date_elem.text if date_elem is not None else ""
        
        # Ignora resumos semanais que agregam varias noticias (pois elas ja aparecem separadamente)
        if "você viu?" in title.lower() or "resumo da semana" in title.lower():
            continue
            
        # Filtra por São João del Rei no titulo ou descricao
        search_text = (title + " " + desc_html).lower()
        if "são joão del rei" not in search_text and "sao joao del rei" not in search_text:
            continue
        
        content = _strip_html(desc_html)
        if not content:
            continue
            
        all_entries.append({
            "titulo": _strip_html(title),
            "descricao": content[:350],
            "conteudo_completo": content,
            "endereco": _extract_address(content),
            "fonte_url": link,
            "fonte_data": pub_date
        })

    print(f"\n[g1] Total de entradas de São João del Rei: {len(all_entries)}")

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=2)

    print(f"[g1] Salvo em: {OUTPUT_FILE}")

if __name__ == "__main__":
    scrape()
