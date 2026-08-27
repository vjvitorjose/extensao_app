"""Popula o Supabase com mil usuarios ficticios para desenvolvimento local."""

import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_USERS = (
	{
		"nome_completo": "Joao Pedro Almeida",
		"telefone": "+55 37 99999-1001",
		"cpf": "52998224725",
		"email": "joao.pedro.teste@example.com",
		"password": "Teste@2026Joao!",
	},
	{
		"nome_completo": "Ana Clara Martins",
		"telefone": "+55 37 99999-1002",
		"cpf": "11144477735",
		"email": "ana.clara.teste@example.com",
		"password": "Teste@2026Ana!",
	},
	{
		"nome_completo": "Lucas Gabriel Costa",
		"telefone": "+55 37 99999-1003",
		"cpf": "93541134780",
		"email": "lucas.gabriel.teste@example.com",
		"password": "Teste@2026Lucas!",
	},
	{
		"nome_completo": "Mariana Beatriz Souza",
		"telefone": "+55 37 99999-1004",
		"cpf": "16899535009",
		"email": "mariana.beatriz.teste@example.com",
		"password": "Teste@2026Mariana!",
	},
	{
		"nome_completo": "Rafael Henrique Oliveira",
		"telefone": "+55 37 99999-1005",
		"cpf": "40171368002",
		"email": "rafael.henrique.teste@example.com",
		"password": "Teste@2026Rafael!",
	},
)


def generate_cpf(index: int) -> str:
	base = f"{100000000 + index:09d}"
	first_sum = sum(int(digit) * weight for digit, weight in zip(base, range(10, 1, -1)))
	first_check = (first_sum * 10) % 11 % 10
	second_base = base + str(first_check)
	second_sum = sum(int(digit) * weight for digit, weight in zip(second_base, range(11, 1, -1)))
	second_check = (second_sum * 10) % 11 % 10
	return second_base + str(second_check)


def generate_users() -> tuple[dict, ...]:
	first_names = ("Pedro", "Julia", "Mateus", "Beatriz", "Gustavo", "Larissa", "Bruno", "Camila", "Diego", "Isabela")
	second_names = ("Miguel", "Helena", "Arthur", "Manuela", "Bernardo", "Valentina", "Davi", "Laura", "Enzo", "Sophia")
	surnames = ("Silva", "Santos", "Lima", "Ferreira", "Pereira", "Carvalho", "Gomes", "Ribeiro", "Alves", "Rocha")
	generated_users = []
	for index in range(1, 996):
		first_name = first_names[(index - 1) % len(first_names)]
		second_name = second_names[((index - 1) // len(first_names)) % len(second_names)]
		surname = surnames[((index - 1) // (len(first_names) * len(second_names))) % len(surnames)]
		generated_users.append(
			{
				"nome_completo": f"{first_name} {second_name} {surname}",
				"telefone": f"+55 37 99999-{2000 + index:04d}",
				"cpf": generate_cpf(index),
				"email": f"usuario.teste.{index:04d}@example.com",
				"password": f"Teste@2026User{index:04d}!",
			}
		)
	return BASE_USERS + tuple(generated_users)


USERS = generate_users()


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


REQUEST_RATE_LIMITER = RequestRateLimiter(2)


def load_dotenv_file() -> None:
	"""Carrega variaveis simples do arquivo .env sem substituir o ambiente."""
	env_path = Path(__file__).resolve().parents[1] / ".env"
	if not env_path.exists():
		return

	for line in env_path.read_text(encoding="utf-8").splitlines():
		line = line.strip()
		if not line or line.startswith("#") or "=" not in line:
			continue
		key, value = line.split("=", 1)
		os.environ.setdefault(key.strip(), value.strip().strip('"\''))


def is_valid_cpf(cpf: str) -> bool:
	"""Valida os dois digitos verificadores de um CPF."""
	digits = "".join(character for character in cpf if character.isdigit())
	if len(digits) != 11 or len(set(digits)) == 1:
		return False

	first_sum = sum(int(digit) * weight for digit, weight in zip(digits[:9], range(10, 1, -1)))
	first_check = (first_sum * 10) % 11 % 10
	if first_check != int(digits[9]):
		return False

	second_sum = sum(int(digit) * weight for digit, weight in zip(digits[:10], range(11, 1, -1)))
	second_check = (second_sum * 10) % 11 % 10
	return second_check == int(digits[10])


def supabase_request(
	base_url: str,
	service_role_key: str,
	path: str,
	method: str,
	payload: dict | None = None,
) -> dict:
	for attempt in range(5):
		REQUEST_RATE_LIMITER.wait()
		request = Request(
			f"{base_url.rstrip('/')}{path}",
			data=json.dumps(payload).encode("utf-8") if payload is not None else None,
			headers={
				"apikey": service_role_key,
				"Authorization": f"Bearer {service_role_key}",
				"Content-Type": "application/json",
				"Prefer": "resolution=merge-duplicates,return=minimal",
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
				wait_time = max(float(retry_after), 1.0)
			except ValueError:
				wait_time = 1.0
			time.sleep(wait_time)

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


def populate_database() -> None:
	load_dotenv_file()
	base_url = os.environ.get("SUPABASE_URL")
	service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
	if not base_url or not service_role_key:
		raise RuntimeError("Defina SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY antes de executar.")
	requests_per_second = float(os.environ.get("SUPABASE_REQUESTS_PER_SECOND", "2"))
	global REQUEST_RATE_LIMITER
	REQUEST_RATE_LIMITER = RequestRateLimiter(requests_per_second)
	auth_users = list_auth_users(base_url, service_role_key)

	for user in USERS:
		if not is_valid_cpf(user["cpf"]):
			raise ValueError(f"CPF invalido no cadastro de {user['nome_completo']}.")

		auth_user = auth_users.get(user["email"].lower())
		if auth_user is None:
			auth_user = supabase_request(
				base_url,
				service_role_key,
				"/auth/v1/admin/users",
				"POST",
				{
					"email": user["email"],
					"password": user["password"],
					"email_confirm": True,
					"user_metadata": {"nome_completo": user["nome_completo"]},
				},
			)
			status = "criado"
		else:
			status = "ja existente"

		supabase_request(
			base_url,
			service_role_key,
			"/rest/v1/profiles?on_conflict=id",
			"POST",
			{
				"id": auth_user["id"],
				"nome_completo": user["nome_completo"],
				"telefone": user["telefone"],
				"cpf": user["cpf"],
			},
		)
		print(f"Usuario {status}: {user['email']}")


if __name__ == "__main__":
	try:
		populate_database()
	except (HTTPError, URLError) as error:
		detail = error.read().decode("utf-8") if isinstance(error, HTTPError) else str(error)
		raise RuntimeError(f"Falha na comunicacao com o Supabase: {detail}") from error
