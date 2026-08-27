"""Cria danger_reports ficticios para usuarios artificiais em Sao Joao del-Rei."""

import json
import os
import random
import time
from pathlib import Path
from runpy import run_path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


USER_POPULATOR_PATH = Path(__file__).with_name("user-populator.py")
REQUESTS_PER_SECOND = 2
REPORTS_PER_USER_MIN = 0
REPORTS_PER_USER_MAX = 3
USERS_PER_EXECUTION = 5
# Limites aproximados da area urbana de Sao Joao del-Rei, MG.
URBAN_LATITUDE_MIN = -21.17
URBAN_LATITUDE_MAX = -21.10
URBAN_LONGITUDE_MIN = -44.30
URBAN_LONGITUDE_MAX = -44.22
URBAN_CENTER_LATITUDE = -21.1355
URBAN_CENTER_LONGITUDE = -44.2616
URBAN_LATITUDE_SPREAD = 0.012
URBAN_LONGITUDE_SPREAD = 0.014

REPORT_TYPES = (
	("assedio", "Relato ficticio de assedio na regiao."),
	("iluminacao_ruim", "Iluminacao insuficiente no local."),
	("perseguicao", "Relato ficticio de perseguicao na regiao."),
	("area_deserta", "Area com pouco movimento de pessoas."),
	("acidente_transito", "Acidente de transito registrado no local."),
	("assalto", "Relato ficticio de assalto na regiao."),
	("furto", "Relato ficticio de furto na regiao."),
	("violencia_fisica", "Relato ficticio de violencia fisica na regiao."),
	("presenca_arma", "Relato ficticio de presenca de arma."),
	("incendio", "Fumaca ou principio de incendio no local."),
	("via_bloqueada", "Via parcialmente bloqueada."),
	("emergencia_medica", "Possivel emergencia medica no local."),
)


class RequestRateLimiter:
	def __init__(self, requests_per_second: float) -> None:
		if requests_per_second <= 0:
			raise ValueError("requests_per_second deve ser maior que zero.")
		self.interval = 1 / requests_per_second
		self.next_allowed_at = 0.0

	def wait(self) -> None:
		now = time.monotonic()
		wait_time = self.next_allowed_at - now
		if wait_time > 0:
			time.sleep(wait_time)
		self.next_allowed_at = max(now, self.next_allowed_at) + self.interval


rate_limiter = RequestRateLimiter(REQUESTS_PER_SECOND)


def load_dotenv_file() -> None:
	env_path = Path(__file__).resolve().parents[1] / ".env"
	if not env_path.exists():
		return

	for line in env_path.read_text(encoding="utf-8").splitlines():
		line = line.strip()
		if not line or line.startswith("#") or "=" not in line:
			continue
		key, value = line.split("=", 1)
		os.environ.setdefault(key.strip(), value.strip().strip('"\''))


def supabase_request(
	base_url: str,
	service_role_key: str,
	path: str,
	method: str,
	payload: dict | None = None,
) -> dict | list:
	for attempt in range(5):
		rate_limiter.wait()
		request = Request(
			f"{base_url.rstrip('/')}{path}",
			data=json.dumps(payload).encode("utf-8") if payload is not None else None,
			headers={
				"apikey": service_role_key,
				"Authorization": f"Bearer {service_role_key}",
				"Content-Type": "application/json",
				"Prefer": "return=minimal",
			},
			method=method,
		)
		try:
			with urlopen(request, timeout=30) as response:
				response_body = response.read().decode("utf-8")
				return json.loads(response_body) if response_body else {}
		except HTTPError as error:
			if error.code != 429 or attempt == 4:
				raise
			retry_after = error.headers.get("Retry-After", "1")
			try:
				time.sleep(max(float(retry_after), 1.0))
			except ValueError:
				time.sleep(1.0)

	raise RuntimeError("Numero maximo de tentativas excedido.")


def list_auth_users(base_url: str, service_role_key: str) -> dict[str, dict]:
	users_response = supabase_request(
		base_url,
		service_role_key,
		"/auth/v1/admin/users?per_page=1000",
		"GET",
	)
	return {
		user["email"].lower(): user
		for user in users_response.get("users", [])
		if user.get("email")
	}


def generate_urban_coordinates(random_generator: random.Random) -> tuple[float, float]:
	latitude = random_generator.gauss(URBAN_CENTER_LATITUDE, URBAN_LATITUDE_SPREAD)
	longitude = random_generator.gauss(URBAN_CENTER_LONGITUDE, URBAN_LONGITUDE_SPREAD)
	latitude = min(max(latitude, URBAN_LATITUDE_MIN), URBAN_LATITUDE_MAX)
	longitude = min(max(longitude, URBAN_LONGITUDE_MIN), URBAN_LONGITUDE_MAX)
	return round(latitude, 6), round(longitude, 6)


def populate_danger_reports() -> None:
	load_dotenv_file()
	base_url = os.environ.get("SUPABASE_URL")
	service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
	if not base_url or not service_role_key:
		raise RuntimeError("Defina SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY antes de executar.")

	random_generator = random.Random(os.environ.get("DANGER_REPORTS_SEED"))
	artificial_users = run_path(str(USER_POPULATOR_PATH), run_name="user_populator")["USERS"]
	auth_users = list_auth_users(base_url, service_role_key)
	missing_users = [
		user["email"]
		for user in artificial_users
		if user["email"].lower() not in auth_users
	]
	if missing_users:
		raise RuntimeError(f"Usuarios artificiais nao encontrados no Auth: {', '.join(missing_users[:5])}")

	reports_created = 0
	selected_users = random_generator.sample(artificial_users, USERS_PER_EXECUTION)
	for user in selected_users:
		user_id = auth_users[user["email"].lower()]["id"]
		report_count = random_generator.randint(max(1, REPORTS_PER_USER_MIN), REPORTS_PER_USER_MAX)
		selected_types = random_generator.sample(REPORT_TYPES, report_count)
		for report_type, description in selected_types:
			latitude, longitude = generate_urban_coordinates(random_generator)
			supabase_request(
				base_url,
				service_role_key,
				"/rest/v1/danger_reports",
				"POST",
				{
					"usuario_id": user_id,
					"tipo_perigo": report_type,
					"descricao": description,
					"latitude": latitude,
					"longitude": longitude,
					"endereco": "Sao Joao del-Rei, MG (dado ficticio)",
				},
			)
			reports_created += 1
		print(f"Alertas processados: {user['email']} ({report_count})")

	print(f"Total de danger_reports criados: {reports_created}")


if __name__ == "__main__":
	try:
		populate_danger_reports()
	except (HTTPError, URLError) as error:
		detail = error.read().decode("utf-8") if isinstance(error, HTTPError) else str(error)
		raise RuntimeError(f"Falha na comunicacao com o Supabase: {detail}") from error
