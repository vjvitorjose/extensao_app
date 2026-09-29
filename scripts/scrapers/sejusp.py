"""Baixa CSVs selecionados do Portal de Dados Abertos de MG (CKAN).

Execucao:
	py scripts\\scrapers\\sejusp.py

Cada CSV mantém somente registros de São João del-Rei e é salvo em
scripts/data/.
"""

import csv
from io import StringIO
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen


BASE_URL = "https://dados.mg.gov.br"
API_URL = f"{BASE_URL}/api/3/action"
ALLOWED_HOSTS = {"dados.mg.gov.br", "www.dados.mg.gov.br"}
USER_AGENT = "vigIA-scraper/1.0 (desenvolvimento local)"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data"
SAO_JOAO_DEL_REI_IBGE = "316250"
MUNICIPALITY_COLUMNS = ("cod_municipio", "municipio_cod", "codigo_municipio_fato")
RESOURCE_URLS = (
	"https://dados.mg.gov.br/dataset/29d89d80-8aaf-438b-a80f-70bb64d10f6f/resource/476f959e-e4bc-4960-b5c4-b3c22fc6fefb/download/crimes_violentos_2026.csv",
	"https://dados.mg.gov.br/dataset/29d89d80-8aaf-438b-a80f-70bb64d10f6f/resource/d23fed6e-c59a-488e-a1da-72c5091edb30/download/crimes_violentos_2025.csv",
	"https://dados.mg.gov.br/dataset/29d89d80-8aaf-438b-a80f-70bb64d10f6f/resource/15ac6aff-1349-4589-8739-76ed7c52b3b0/download/crimes_violentos_2024.csv",
	"https://dados.mg.gov.br/dataset/1575edab-b294-41fc-bdbc-bcd16891e0cf/resource/bc716a93-c83e-456f-a235-3ffd96e9d094/download/feminicidio_2026.csv",
	"https://dados.mg.gov.br/dataset/1575edab-b294-41fc-bdbc-bcd16891e0cf/resource/1afc4e40-3e53-49ce-96a1-f0df6a625459/download/feminicidio_2025.csv",
	"https://dados.mg.gov.br/dataset/1575edab-b294-41fc-bdbc-bcd16891e0cf/resource/c7ce4edb-0ce4-4928-bd72-07e23b06cebe/download/feminicidio_2024.csv",
	"https://dados.mg.gov.br/dataset/1575edab-b294-41fc-bdbc-bcd16891e0cf/resource/b513d8f7-b016-4b40-a7ba-426721a8fd8f/download/violencia_domestica_2026.csv",
	"https://dados.mg.gov.br/dataset/1575edab-b294-41fc-bdbc-bcd16891e0cf/resource/b339e530-586f-4128-81d0-7a327ff20b7e/download/violencia_domestica_2025.csv",
	"https://dados.mg.gov.br/dataset/1575edab-b294-41fc-bdbc-bcd16891e0cf/resource/9df0c395-8b88-4a78-8dd5-c710ecd14758/download/violencia_domestica_2024.csv",
	"https://dados.mg.gov.br/dataset/7bc9e173-d008-4616-9a6f-5bd76ef5bd8d/resource/ba926007-87e3-46ac-a7db-29bafa4b1e83/download/vitimas_acidente_transito_2026.csv",
	"https://dados.mg.gov.br/dataset/7bc9e173-d008-4616-9a6f-5bd76ef5bd8d/resource/e638ea2a-36db-466e-a341-bc4bb887fe77/download/vitimas_acidente_transito_2025.csv",
	"https://dados.mg.gov.br/dataset/7bc9e173-d008-4616-9a6f-5bd76ef5bd8d/resource/5e9615f9-bce3-4111-8c7b-8853be1e23ff/download/vitimas_acidente_transito_2024.csv",
)


def _fetch_json(url: str) -> dict:
	request = Request(url, headers={"User-Agent": USER_AGENT})
	with urlopen(request, timeout=30) as response:
		return json.loads(response.read().decode("utf-8"))


def _resource_id_from_url(resource_url: str) -> str:
	parsed = urlparse(resource_url)
	if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
		raise ValueError("Use um link HTTPS de recurso do Portal de Dados Abertos de MG.")

	segments = [segment for segment in parsed.path.split("/") if segment]
	try:
		resource_index = segments.index("resource")
		resource_id = segments[resource_index + 1]
	except (ValueError, IndexError) as exc:
		raise ValueError("O link precisa apontar para a página ou download de um recurso.") from exc

	if not re.fullmatch(r"[0-9a-fA-F-]{36}", resource_id):
		raise ValueError(f"ID de recurso CKAN inválido no link: {resource_id}")
	return resource_id


def _safe_filename(value: str) -> str:
	filename = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
	return filename or "recurso.csv"


def _filter_csv_content(content: bytes) -> tuple[bytes, int, int]:
	try:
		text = content.decode("utf-8-sig")
	except UnicodeDecodeError:
		text = content.decode("cp1252")

	reader = csv.reader(StringIO(text, newline=""), delimiter=";")
	try:
		header = next(reader)
	except StopIteration as exc:
		raise ValueError("O CSV recebido está vazio.") from exc

	try:
		municipality_index = next(
			index for index, column in enumerate(header)
			if column.strip().lower() in MUNICIPALITY_COLUMNS
		)
	except StopIteration as exc:
		raise ValueError(
			"Não foi encontrada uma coluna de código municipal conhecida no CSV."
		) from exc

	output = StringIO(newline="")
	writer = csv.writer(output, delimiter=";", lineterminator="\n")
	writer.writerow(header)
	rows_read = 0
	rows_saved = 0
	for row in reader:
		if not row:
			continue
		rows_read += 1
		if municipality_index >= len(row):
			continue
		municipality_code = row[municipality_index].strip().replace(",", ".")
		if re.fullmatch(rf"{SAO_JOAO_DEL_REI_IBGE}(?:\.0+)?", municipality_code):
			writer.writerow(row)
			rows_saved += 1

	return output.getvalue().encode("utf-8"), rows_read, rows_saved


def _fetch_action(action: str, **params: str) -> dict:
	query = urlencode(params)
	response = _fetch_json(f"{API_URL}/{action}?{query}")
	if not response.get("success"):
		raise RuntimeError(f"A API CKAN retornou erro em {action}: {response.get('error')}")
	return response["result"]


def _download_resource(resource_page_url: str) -> Path:
	resource_id = _resource_id_from_url(resource_page_url)
	resource = _fetch_action("resource_show", id=resource_id)
	if str(resource.get("format", "")).strip().lower() != "csv":
		raise ValueError(
			f"O recurso '{resource.get('name', resource_id)}' não está identificado como CSV."
		)

	download_url = resource.get("url", "")
	parsed_download = urlparse(download_url)
	if parsed_download.hostname not in ALLOWED_HOSTS:
		raise ValueError(f"URL de download fora do portal oficial: {download_url}")
	if parsed_download.scheme != "https":
		parsed_download = parsed_download._replace(scheme="https")
		download_url = urlunparse(parsed_download)

	request = Request(download_url, headers={"User-Agent": USER_AGENT})
	with urlopen(request, timeout=60) as response:
		source_content = response.read()
		content_type = response.headers.get_content_type()
		if content_type == "text/html":
			raise ValueError(f"O download do recurso retornou HTML, não CSV: {download_url}")
	content, rows_downloaded, rows_saved = _filter_csv_content(source_content)

	suggested_filename = Path(urlparse(download_url).path).name
	filename = _safe_filename(suggested_filename or resource.get("name", "recurso.csv"))
	if not filename.lower().endswith(".csv"):
		filename += ".csv"

	OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
	destination = OUTPUT_DIR / filename
	destination.write_bytes(content)

	print(
		f"[sejusp] Salvo: {destination} "
		f"({rows_saved:,}/{rows_downloaded:,} linhas; {len(content):,} bytes)"
	)
	return destination


def main() -> None:
	for resource_url in RESOURCE_URLS:
		try:
			_download_resource(resource_url)
		except (HTTPError, URLError) as exc:
			raise RuntimeError(f"Falha ao acessar o recurso SEJUSP: {exc}") from exc


if __name__ == "__main__":
	main()
