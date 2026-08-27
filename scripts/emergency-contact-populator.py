"""Cadastra contatos de emergencia ficticios para um usuario de teste."""

import json
import os
from runpy import run_path
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


USER_POPULATOR_PATH = Path(__file__).with_name("user-populator.py")
REQUESTS_PER_SECOND = 2


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


def list_existing_contacts(base_url: str, service_role_key: str) -> set[tuple[str, str]]:
	contacts = supabase_request(
		base_url,
		service_role_key,
		"/rest/v1/emergency_contacts?select=profile_id,email&limit=100000",
		"GET",
	)
	return {
		(contact["profile_id"], contact["email"].lower())
		for contact in contacts
		if contact.get("profile_id") and contact.get("email")
	}


def populate_emergency_contacts() -> None:
	load_dotenv_file()
	base_url = os.environ.get("SUPABASE_URL")
	service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
	if not base_url or not service_role_key:
		raise RuntimeError("Defina SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY antes de executar.")

	artificial_users = run_path(str(USER_POPULATOR_PATH), run_name="user_populator")['USERS']
	auth_users = list_auth_users(base_url, service_role_key)
	existing_contacts = list_existing_contacts(base_url, service_role_key)
	artificial_auth_users = [
		(user, auth_users.get(user["email"].lower()))
		for user in artificial_users
	]
	missing_users = [user["email"] for user, auth_user in artificial_auth_users if auth_user is None]
	if missing_users:
		raise RuntimeError(f"Usuarios artificiais nao encontrados no Auth: {', '.join(missing_users[:5])}")

	user_count = len(artificial_auth_users)
	for index, (target_data, target_auth) in enumerate(artificial_auth_users):
		for contact_offset in (1, 2):
			contact_data, contact_auth = artificial_auth_users[(index + contact_offset) % user_count]
			contact_key = (target_auth["id"], contact_data["email"].lower())
			if contact_key in existing_contacts:
				continue

			supabase_request(
				base_url,
				service_role_key,
				"/rest/v1/emergency_contacts",
				"POST",
				{
					"profile_id": target_auth["id"],
					"nome": contact_data["nome_completo"],
					"telefone": contact_data["telefone"],
					"email": contact_data["email"],
					"parentesco": "Amigo",
				},
			)
			existing_contacts.add(contact_key)
		print(f"Contatos processados: {target_data['email']}")


if __name__ == "__main__":
	try:
		populate_emergency_contacts()
	except (HTTPError, URLError) as error:
		detail = error.read().decode("utf-8") if isinstance(error, HTTPError) else str(error)
		raise RuntimeError(f"Falha na comunicacao com o Supabase: {detail}") from error
