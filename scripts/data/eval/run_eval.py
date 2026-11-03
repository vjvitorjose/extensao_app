# -*- coding: utf-8 -*-
"""Executa a avaliação few-shot/zero-shot dos LLMs sobre os 120 posts.

O mesmo prompt é usado para todos os provedores. Cada resposta é gravada
imediatamente em JSONL, com latência, resposta crua, JSON parseado e erros,
permitindo retomar uma execução interrompida.

Provedores:
    opencode/<modelo>   API local de sessões do OpenCode (big-pickle, DeepSeek)
    deepseek/<modelo>   API local de sessões do OpenCode (DeepSeek pago)
    gemini/<modelo>     API Google Generative Language (Gemini)
    ollama/<modelo>     API local do Ollama (modelo gratuito local)

Exemplos:
    python scripts/data/eval/run_eval.py --model opencode/big-pickle
    python scripts/data/eval/run_eval.py --model gemini/gemini-3.8-flash --limit 20
    python scripts/data/eval/run_eval.py --model ollama/qwen3:8b
    python scripts/data/eval/run_eval.py --model opencode/big-pickle --ids sjd-001,sjd-012
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import random
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

from _eval_common import (
    BASE,
    BLIND,
    FEW_SHOT,
    build_prompt,
    load_env_file,
    normalize_prediction,
    parse_json_output,
    read_jsonl,
    safe_model_name,
)

try:  # Python 3.7+
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass

RUNS_DIR = BASE / "runs"
DEFAULT_TIMEOUT = 300
PROMPT_VERSION = "2026-11-03.fewshot.v1"

DEFAULT_MODELS = [
    "opencode/big-pickle",
    "opencode/deepseek-v4.1-flash-free",
    "gemini/gemini-3.8-flash",
    "ollama/qwen3:8b",
]


# ---------------------------------------------------------------------------
# Erros e utilidades HTTP
# ---------------------------------------------------------------------------


class ProviderError(RuntimeError):
    """Falha de um provedor. `retryable` indica se vale tentar de novo."""

    def __init__(self, message: str, *, retryable: bool = False, status: int | None = None):
        super().__init__(message)
        self.retryable = retryable
        self.status = status


class QuotaExceeded(ProviderError):
    """Cota diária esgotada: não adianta insistir hoje."""

    def __init__(self, message: str, retry_after_s: float | None = None):
        super().__init__(message, retryable=False, status=429)
        self.retry_after_s = retry_after_s


def _http_json(
    method: str,
    url: str,
    *,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[int, dict[str, Any] | None, str]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = request.Request(url, data=data, method=method)
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            parsed = json.loads(raw) if raw.strip() else None
            return resp.status, parsed, raw
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(raw) if raw.strip() else None
        except json.JSONDecodeError:
            parsed = None
        return exc.code, parsed, raw
    except error.URLError as exc:
        raise ProviderError(f"falha de rede: {exc.reason}", retryable=True) from exc
    except TimeoutError as exc:
        raise ProviderError("timeout na requisição", retryable=True) from exc


# ---------------------------------------------------------------------------
# OpenCode (API local de sessões)
# ---------------------------------------------------------------------------


def _find_opencode_service() -> tuple[str, str]:
    """Descobre URL e senha do servidor local do OpenCode."""
    candidates = [
        Path.home() / ".local" / "state" / "opencode" / "service.json",
        Path.home() / ".config" / "opencode" / "service.json",
        Path(os.environ.get("OPENCODE_STATE_DIR", "")) / "service.json"
        if os.environ.get("OPENCODE_STATE_DIR")
        else None,
    ]
    url = os.environ.get("OPENCODE_SERVER_URL")
    password = os.environ.get("OPENCODE_SERVER_PASSWORD")

    for path in candidates:
        if path is None or not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        url = url or data.get("url")
        password = password or data.get("password")
        if url and password:
            break

    if not url:
        raise ProviderError(
            "servidor local do OpenCode não encontrado; abra o OpenCode ou defina "
            "OPENCODE_SERVER_URL"
        )
    if not password:
        raise ProviderError(
            "senha do servidor local do OpenCode não encontrada; defina "
            "OPENCODE_SERVER_PASSWORD"
        )
    return url.rstrip("/"), password


@dataclass
class ProviderResult:
    text: str
    latency_s: float
    usage: dict[str, Any] = field(default_factory=dict)
    cost_usd: float = 0.0


class OpenCodeService:
    def __init__(self, model_ref: str, *, timeout: float = DEFAULT_TIMEOUT):
        self.base_url, self.password = _find_opencode_service()
        self.timeout = timeout
        self.model_ref = model_ref
        provider_id, model_id = parse_model_ref(model_ref)
        if provider_id not in {"opencode", "deepseek"}:
            raise ProviderError(
                "modelo de sessão do OpenCode deve usar o provedor 'opencode' ou "
                f"'deepseek', recebido {provider_id!r}"
            )
        self.provider_id = provider_id
        self.model_id = model_id
        token = base64.b64encode(f"opencode:{self.password}".encode()).decode()
        self.headers = {"Authorization": f"Basic {token}"}

    def _call(
        self, method: str, path: str, body: dict[str, Any] | None = None
    ) -> tuple[int, dict[str, Any] | None, str]:
        return _http_json(
            method,
            self.base_url + path,
            body=body,
            headers=self.headers,
            timeout=self.timeout,
        )

    def create_session(self, title: str) -> str:
        status, data, raw = self._call(
            "POST",
            "/api/session",
            {
                "title": title,
                "model": {"providerID": self.provider_id, "id": self.model_id},
                "agent": "build",
            },
        )
        if status != 200 or not data or "data" not in data:
            raise ProviderError(
                f"não foi possível criar sessão OpenCode (HTTP {status}): {raw[:300]}",
                retryable=status >= 500,
                status=status,
            )
        return data["data"]["id"]

    def delete_session(self, session_id: str) -> None:
        try:
            self._call("DELETE", f"/api/session/{session_id}")
        except ProviderError:
            pass

    def generate(self, session_id: str, prompt: str) -> str:
        status, data, raw = self._call(
            "POST",
            f"/api/session/{session_id}/generate",
            {"prompt": prompt},
        )
        if status != 200 or not data or "data" not in data:
            message = raw[:500]
            retryable = status in {408, 409, 425, 429, 500, 502, 503, 504}
            if status == 404:
                raise ProviderError(
                    f"sessão OpenCode não encontrada: {message}", retryable=True, status=status
                )
            raise ProviderError(
                f"OpenCode HTTP {status}: {message}", retryable=retryable, status=status
            )
        text = (data.get("data") or {}).get("text")
        if not isinstance(text, str):
            raise ProviderError("resposta do OpenCode sem campo data.text", retryable=True)
        return text


class OpenCodeProvider:
    """Um provedor, uma sessão nova por requisição.

    O limite gratuito do OpenCode é por sessão: a primeira geração de cada
    sessão passa, a segunda recebe HTTP 503 "Free usage limit reached". Por
    isso não reaproveitamos sessões entre itens.
    """

    def __init__(self, model_ref: str, *, timeout: float = DEFAULT_TIMEOUT):
        self.model_ref = model_ref
        self.service = OpenCodeService(model_ref, timeout=timeout)
        self._lock = threading.Lock()
        self._session_counter = 0
        self.default_concurrency = 2

    @property
    def name(self) -> str:
        return self.model_ref

    def _new_session(self) -> str:
        with self._lock:
            self._session_counter += 1
            index = self._session_counter
        return self.service.create_session(
            f"eval-{safe_model_name(self.model_ref)}-{index:02d}"
        )

    def complete(self, prompt: str) -> ProviderResult:
        started = time.perf_counter()
        session_id = self._new_session()
        try:
            text = self.service.generate(session_id, prompt)
        except ProviderError as exc:
            if exc.status == 404:
                # A sessão pode ter sido encerrada pelo servidor; recria uma vez.
                session_id = self._new_session()
                text = self.service.generate(session_id, prompt)
            else:
                raise
        finally:
            self.service.delete_session(session_id)
        return ProviderResult(text=text, latency_s=time.perf_counter() - started)

    def close(self) -> None:
        return None


# ---------------------------------------------------------------------------
# Gemini (API Google)
# ---------------------------------------------------------------------------


# Preços públicos aproximados por milhão de tokens, usados apenas como
# referência. O plano gratuito desta conta é 0; o custo é recalculado se o
# usuário definir GEMINI_PRICE_INPUT / GEMINI_PRICE_OUTPUT no .env.
GEMINI_PRICES = {
    "gemini-3.8-flash": (0.0, 0.0),
    "gemini-3.7-flash": (0.0, 0.0),
    "gemini-3.5-flash": (0.0, 0.0),
    "gemini-3.1-flash-lite": (0.0, 0.0),
    "gemini-2.5-flash": (0.0, 0.0),
}


class GeminiProvider:
    def __init__(self, model_ref: str, *, timeout: float = DEFAULT_TIMEOUT):
        load_env_file()
        provider, model = parse_model_ref(model_ref)
        if provider != "gemini":
            raise ProviderError(f"provedor Gemini inválido: {provider!r}")
        self.model = model
        self.model_ref = model_ref
        self.api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not self.api_key:
            raise ProviderError("GEMINI_API_KEY não definida em scripts/.env")
        self.timeout = timeout
        self.default_concurrency = 1
        self._response_mime = True

    @property
    def name(self) -> str:
        return self.model_ref

    def _price(self) -> tuple[float, float]:
        env_in = os.environ.get("GEMINI_PRICE_INPUT")
        env_out = os.environ.get("GEMINI_PRICE_OUTPUT")
        if env_in is not None and env_out is not None:
            try:
                return float(env_in), float(env_out)
            except ValueError:
                pass
        return GEMINI_PRICES.get(self.model, (0.0, 0.0))

    def complete(self, prompt: str) -> ProviderResult:
        generation_config: dict[str, Any] = {
            "temperature": 0,
            "maxOutputTokens": 2048,
        }
        if self._response_mime:
            generation_config["responseMimeType"] = "application/json"
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": generation_config,
        }
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        started = time.perf_counter()
        status, data, raw = _http_json(
            "POST", url, body=body, timeout=self.timeout
        )
        if status == 400 and self._response_mime and "response" in raw.lower() and "mime" in raw.lower():
            # Alguns modelos não aceitam responseMimeType; tenta sem forçar JSON.
            self._response_mime = False
            return self.complete(prompt)
        if status == 429:
            message = raw[:800]
            retry_after = _retry_after_seconds(data)
            if "perday" in message.lower() or "per day" in message.lower() or "daily" in message.lower():
                raise QuotaExceeded(f"cota diária do Gemini esgotada: {message}", retry_after)
            raise ProviderError(
                f"Gemini HTTP 429 (limite por minuto): {message}",
                retryable=True,
                status=status,
            )
        if status != 200 or not data:
            raise ProviderError(
                f"Gemini HTTP {status}: {raw[:600]}",
                retryable=status in {408, 425, 500, 502, 503, 504},
                status=status,
            )

        candidates = data.get("candidates") or []
        if not candidates:
            feedback = data.get("promptFeedback") or {}
            raise ProviderError(
                f"Gemini sem candidatos (promptFeedback={json.dumps(feedback, ensure_ascii=False)[:300]})",
                retryable=True,
            )
        candidate = candidates[0]
        finish = candidate.get("finishReason")
        if finish and finish not in {"STOP", "MAX_TOKENS"}:
            raise ProviderError(f"Gemini bloqueou a resposta: finishReason={finish}", retryable=False)
        parts = ((candidate.get("content") or {}).get("parts") or [])
        text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        if finish == "MAX_TOKENS" and text:
            # JSON possivelmente incompleto; o parser vai acusar.
            pass

        usage_raw = data.get("usageMetadata") or {}
        usage = {
            "prompt_tokens": usage_raw.get("promptTokenCount"),
            "output_tokens": usage_raw.get("candidatesTokenCount"),
            "thought_tokens": usage_raw.get("thoughtsTokenCount"),
            "total_tokens": usage_raw.get("totalTokenCount"),
        }
        price_in, price_out = self._price()
        cost = (
            (usage.get("prompt_tokens") or 0) / 1_000_000 * price_in
            + (usage.get("output_tokens") or 0) / 1_000_000 * price_out
        )
        return ProviderResult(
            text=text,
            latency_s=time.perf_counter() - started,
            usage=usage,
            cost_usd=cost,
        )

    def close(self) -> None:
        return None


def _retry_after_seconds(data: dict[str, Any] | None) -> float | None:
    if not data:
        return None
    details = (data.get("error") or {}).get("details") or []
    for detail in details:
        if detail.get("@type", "").endswith("RetryInfo"):
            delay = detail.get("retryDelay")
            if isinstance(delay, str) and delay.endswith("s"):
                try:
                    return float(delay[:-1])
                except ValueError:
                    return None
    return None


# ---------------------------------------------------------------------------
# Ollama (modelo local)
# ---------------------------------------------------------------------------


class OllamaProvider:
    """Modelo local via API do Ollama (`/api/chat`), sem custo por token."""

    def __init__(self, model_ref: str, *, timeout: float = DEFAULT_TIMEOUT):
        provider, model = parse_model_ref(model_ref)
        if provider != "ollama":
            raise ProviderError(f"provedor Ollama inválido: {provider!r}")
        self.model = model
        self.model_ref = model_ref
        self.base_url = (
            os.environ.get("OLLAMA_BASE_URL")
            or os.environ.get("OLLAMA_HOST")
            or "http://127.0.0.1:11434"
        ).rstrip("/")
        if not self.base_url.startswith(("http://", "https://")):
            self.base_url = "http://" + self.base_url
        self.timeout = timeout
        self.default_concurrency = 1
        self._use_think_false = True

    @property
    def name(self) -> str:
        return self.model_ref

    def _payload(self, prompt: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0,
                "top_p": 0.9,
                "num_ctx": int(os.environ.get("OLLAMA_NUM_CTX", "16384")),
                "num_predict": int(os.environ.get("OLLAMA_NUM_PREDICT", "1024")),
                "repeat_penalty": 1.05,
            },
        }
        if self._use_think_false:
            payload["think"] = False
        return payload

    def complete(self, prompt: str) -> ProviderResult:
        started = time.perf_counter()
        status, data, raw = _http_json(
            "POST",
            self.base_url + "/api/chat",
            body=self._payload(prompt),
            timeout=self.timeout,
        )
        if status == 400 and self._use_think_false and "think" in raw.lower():
            self._use_think_false = False
            return self.complete(prompt)
        if status == 404:
            raise ProviderError(
                f"modelo Ollama não encontrado ({self.model}); rode "
                f"`ollama pull {self.model}`. Resposta: {raw[:300]}",
                retryable=False,
                status=status,
            )
        if status != 200 or not data:
            raise ProviderError(
                f"Ollama HTTP {status}: {raw[:600]}",
                retryable=status in {408, 425, 429, 500, 502, 503, 504},
                status=status,
            )
        message = data.get("message") or {}
        text = message.get("content")
        if not isinstance(text, str) or not text.strip():
            thinking = message.get("thinking")
            if isinstance(thinking, str) and thinking.strip():
                text = thinking
            else:
                raise ProviderError("resposta do Ollama sem conteúdo", retryable=True)
        usage = {
            "prompt_tokens": data.get("prompt_eval_count"),
            "output_tokens": data.get("eval_count"),
            "total_tokens": (data.get("prompt_eval_count") or 0)
            + (data.get("eval_count") or 0),
            "total_duration_ns": data.get("total_duration"),
            "load_duration_ns": data.get("load_duration"),
        }
        return ProviderResult(
            text=text,
            latency_s=time.perf_counter() - started,
            usage=usage,
            cost_usd=0.0,
        )

    def close(self) -> None:
        return None


# ---------------------------------------------------------------------------
# Fábrica e refs de modelo
# ---------------------------------------------------------------------------


def parse_model_ref(model_ref: str) -> tuple[str, str]:
    if "/" not in model_ref:
        # Atalho: nomes conhecidos do OpenCode.
        return "opencode", model_ref
    provider, model = model_ref.split("/", 1)
    return provider.strip().lower(), model.strip()


def make_provider(
    model_ref: str, *, timeout: float
) -> OpenCodeProvider | GeminiProvider | OllamaProvider:
    provider, _ = parse_model_ref(model_ref)
    if provider in {"opencode", "deepseek"}:
        return OpenCodeProvider(model_ref, timeout=timeout)
    if provider == "gemini":
        return GeminiProvider(model_ref, timeout=timeout)
    if provider == "ollama":
        return OllamaProvider(model_ref, timeout=timeout)
    raise ProviderError(
        f"provedor desconhecido: {provider!r} "
        "(use opencode/..., deepseek/..., gemini/... ou ollama/...)"
    )


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RateLimiter:
    """Limita a taxa global de requisições, mesmo com várias threads."""

    def __init__(self, interval_s: float):
        self.interval_s = max(0.0, interval_s)
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self) -> None:
        if self.interval_s <= 0:
            return
        with self._lock:
            now = time.monotonic()
            if self._next > now:
                delay = self._next - now
            else:
                delay = 0.0
            self._next = max(now, self._next) + self.interval_s
        if delay > 0:
            time.sleep(delay)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_items(ids: list[str] | None, limit: int | None) -> list[dict[str, Any]]:
    items = read_jsonl(BLIND)
    if ids:
        wanted = {item.strip() for item in ids if item.strip()}
        missing = wanted - {item["id"] for item in items}
        if missing:
            raise SystemExit(f"IDs não encontrados na amostra: {sorted(missing)}")
        items = [item for item in items if item["id"] in wanted]
    if limit is not None:
        items = items[:limit]
    return items


def load_done(path: Path, *, retry_parse_errors: bool) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Lê um run existente e devolve (últimos registros por id, todos os registros)."""
    if not path.exists():
        return {}, []
    records = read_jsonl(path)
    latest: dict[str, dict[str, Any]] = {}
    for record in records:
        item_id = record.get("id")
        if item_id:
            latest[item_id] = record
    done: dict[str, dict[str, Any]] = {}
    for item_id, record in latest.items():
        if record.get("error"):
            continue
        if record.get("parse_error") and not retry_parse_errors:
            continue
        done[item_id] = record
    return done, records


def write_summary(
    path: Path,
    *,
    model_ref: str,
    mode: str,
    status: str,
    selected: int,
    records: list[dict[str, Any]],
    started_at: str,
    finished_at: str,
    extra: dict[str, Any] | None = None,
) -> None:
    latest: dict[str, dict[str, Any]] = {}
    for record in records:
        latest[record["id"]] = record
    values = list(latest.values())
    summary = {
        "model": model_ref,
        "mode": mode,
        "status": status,
        "selected": selected,
        "records": len(values),
        "ok": sum(1 for r in values if not r.get("error") and not r.get("parse_error")),
        "errors": sum(1 for r in values if r.get("error")),
        "parse_errors": sum(1 for r in values if not r.get("error") and r.get("parse_error")),
        "total_latency_s": round(sum(r.get("latency_s") or 0 for r in values), 3),
        "mean_latency_s": round(
            sum(r.get("latency_s") or 0 for r in values) / len(values), 3
        )
        if values
        else None,
        "total_cost_usd": round(sum(r.get("cost_usd") or 0 for r in values), 8),
        "started_at": started_at,
        "finished_at": finished_at,
    }
    if extra:
        summary["extra"] = extra
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    items = load_items(args.ids.split(",") if args.ids else None, args.limit)
    few_shot_path = Path(args.few_shot) if args.few_shot else FEW_SHOT
    few_shot = read_jsonl(few_shot_path) if args.mode == "few_shot" else []
    if args.mode == "few_shot" and not few_shot:
        raise SystemExit(f"{few_shot_path} vazio; rode _build_few_shot.py")

    provider = make_provider(args.model, timeout=args.timeout)
    run_name = args.run_name or f"{safe_model_name(args.model)}_{args.mode}"
    out_path = Path(args.out) if args.out else RUNS_DIR / f"{run_name}.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path = out_path.with_suffix(".summary.json")
    meta_path = out_path.with_suffix(".meta.json")

    done, existing = load_done(out_path, retry_parse_errors=args.retry_parse_errors)
    pending = [item for item in items if item["id"] not in done]
    if args.shuffle:
        random.Random(args.seed).shuffle(pending)

    if args.dry_run:
        sample = pending[0] if pending else items[0]
        prompt = build_prompt(sample, few_shot, few_shot_enabled=args.mode == "few_shot")
        print(
            json.dumps(
                {
                    "model": args.model,
                    "mode": args.mode,
                    "items": len(items),
                    "pending": len(pending),
                    "few_shot_examples": len(few_shot),
                    "prompt_chars": len(prompt),
                    "prompt_approx_tokens": len(prompt) // 4,
                    "out": str(out_path),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    meta = {
        "model": args.model,
        "mode": args.mode,
        "run_name": run_name,
        "out": str(out_path),
        "selected": len(items),
        "pending_at_start": len(pending),
        "already_done": len(done),
        "few_shot_examples": len(few_shot),
        "few_shot_file": str(few_shot_path),
        "few_shot_sha256": sha256_text(few_shot_path.read_text(encoding="utf-8")),
        "prompt_version": PROMPT_VERSION,
        "prompt_common_sha256": sha256_text(
            (BASE / "_eval_common.py").read_text(encoding="utf-8")
        ),
        "started_at": now_iso(),
        "args": {key: value for key, value in vars(args).items() if key != "func"},
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    concurrency = args.concurrency or provider.default_concurrency
    concurrency = max(1, min(concurrency, max(1, len(pending))))
    limiter = RateLimiter(args.delay)
    write_lock = threading.Lock()
    abort_event = threading.Event()
    all_records = list(existing)
    started_at = meta["started_at"]
    quota_error: str | None = None

    def append_record(record: dict[str, Any]) -> None:
        with write_lock:
            with out_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            all_records.append(record)

    def classify(item: dict[str, Any]) -> dict[str, Any]:
        if abort_event.is_set():
            raise QuotaExceeded("execução abortada")
        prompt = build_prompt(item, few_shot, few_shot_enabled=args.mode == "few_shot")
        attempts = 0
        last_error = "erro desconhecido"
        while attempts < args.attempts:
            attempts += 1
            if abort_event.is_set():
                raise QuotaExceeded("execução abortada")
            try:
                limiter.wait()
                result = provider.complete(prompt)
            except QuotaExceeded as exc:
                abort_event.set()
                raise exc
            except ProviderError as exc:
                last_error = str(exc)
                if not exc.retryable or attempts >= args.attempts:
                    break
                delay = min(args.backoff_max, args.backoff_base * (2 ** (attempts - 1)))
                delay *= 1 + random.random() * 0.3
                print(
                    f"  retry {item['id']} tentativa {attempts}/{args.attempts} em {delay:.1f}s: {exc}",
                    file=sys.stderr,
                )
                time.sleep(delay)
                continue
            except Exception as exc:  # noqa: BLE001 - registra e segue
                last_error = f"{type(exc).__name__}: {exc}"
                break

            parsed, parse_error = parse_json_output(result.text)
            normalized = normalize_prediction(parsed) if parsed is not None else None
            return {
                "id": item["id"],
                "model": args.model,
                "mode": args.mode,
                "timestamp": now_iso(),
                "attempts": attempts,
                "latency_s": round(result.latency_s, 3),
                "prompt_chars": len(prompt),
                "prompt_sha256": sha256_text(prompt),
                "raw_response": result.text,
                "usage": result.usage,
                "cost_usd": result.cost_usd,
                "parse_error": parse_error,
                "parsed": normalized,
                "error": None,
            }

        return {
            "id": item["id"],
            "model": args.model,
            "mode": args.mode,
            "timestamp": now_iso(),
            "attempts": attempts,
            "latency_s": None,
            "prompt_chars": len(prompt),
            "prompt_sha256": sha256_text(prompt),
            "raw_response": None,
            "usage": {},
            "cost_usd": 0.0,
            "parse_error": None,
            "parsed": None,
            "error": last_error,
        }

    total = len(pending)
    completed = 0
    t0 = time.perf_counter()
    print(
        f"modelo={args.model} modo={args.mode} itens={len(items)} "
        f"pendentes={total} concorrencia={concurrency} saida={out_path}"
    )

    try:
        if concurrency == 1 or total == 0:
            for item in pending:
                if abort_event.is_set():
                    break
                record = classify(item)
                append_record(record)
                completed += 1
                _print_progress(record, completed, total, t0)
        else:
            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                futures = {pool.submit(classify, item): item for item in pending}
                pending_futures = set(futures)
                while pending_futures:
                    done_set, pending_futures = wait(
                        pending_futures, return_when=FIRST_COMPLETED, timeout=1
                    )
                    for future in done_set:
                        item = futures[future]
                        try:
                            record = future.result()
                        except QuotaExceeded as exc:
                            quota_error = str(exc)
                            abort_event.set()
                            continue
                        append_record(record)
                        completed += 1
                        _print_progress(record, completed, total, t0)
                    if abort_event.is_set():
                        for future in pending_futures:
                            future.cancel()
                        break
    except KeyboardInterrupt:
        abort_event.set()
        status = "interrompido"
    except QuotaExceeded as exc:
        quota_error = str(exc)
        status = "cota_esgotada"
    except Exception as exc:  # noqa: BLE001 - registra falha e encerra com resumo
        abort_event.set()
        quota_error = f"{type(exc).__name__}: {exc}"
        status = "erro_fatal"
    else:
        status = "cota_esgotada" if quota_error else ("concluido" if completed == total else "parcial")
    finally:
        provider.close()

    finished_at = now_iso()
    write_summary(
        summary_path,
        model_ref=args.model,
        mode=args.mode,
        status=status,
        selected=len(items),
        records=all_records,
        started_at=started_at,
        finished_at=finished_at,
        extra={"quota_error": quota_error} if quota_error else None,
    )
    _dedupe_file(out_path)
    print(
        f"fim status={status} concluidos_nesta_execucao={completed}/{total} "
        f"total_no_arquivo={len(read_jsonl(out_path))} resumo={summary_path}"
    )
    if quota_error:
        print(f"cota: {quota_error}", file=sys.stderr)
        return 2
    return 0 if completed == total else 1


def _print_progress(record: dict[str, Any], completed: int, total: int, t0: float) -> None:
    if record.get("error"):
        result = f"ERRO {record['error'][:80]}"
    elif record.get("parse_error"):
        result = f"JSON_INVALIDO {record['parse_error']}"
    else:
        parsed = record.get("parsed") or {}
        result = (
            f"tipo={parsed.get('tipo_perigo')} "
            f"relevante={parsed.get('relevante')} "
            f"fora={parsed.get('fora_da_area')} "
            f"conf={parsed.get('confianca')}"
        )
    elapsed = time.perf_counter() - t0
    rate = completed / elapsed if elapsed > 0 else 0
    eta = (total - completed) / rate if rate > 0 else 0
    print(
        f"[{completed:03d}/{total:03d}] {record['id']} {result} "
        f"({record.get('latency_s')}s, eta {eta/60:.1f}min)"
    )


def _dedupe_file(path: Path) -> None:
    if not path.exists():
        return
    records = read_jsonl(path)
    latest: dict[str, dict[str, Any]] = {}
    for record in records:
        latest[record["id"]] = record
    ordered = [latest[item_id] for item_id in sorted(latest)]
    if len(ordered) != len(records):
        path.write_text(
            "\n".join(json.dumps(record, ensure_ascii=False) for record in ordered) + "\n",
            encoding="utf-8",
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--model",
        default=DEFAULT_MODELS[0],
        help="modelo no formato provedor/modelo (ex.: opencode/big-pickle)",
    )
    parser.add_argument(
        "--mode",
        choices=["few_shot", "zero_shot"],
        default="few_shot",
        help="usar os 26 exemplos few-shot ou prompt zero-shot",
    )
    parser.add_argument("--limit", type=int, default=None, help="limita o número de itens")
    parser.add_argument("--ids", default=None, help="lista de IDs separada por vírgula")
    parser.add_argument(
        "--few-shot",
        default=None,
        help="arquivo JSONL de exemplos few-shot (padrão: few_shot_examples.jsonl)",
    )
    parser.add_argument("--out", default=None, help="arquivo JSONL de saída")
    parser.add_argument("--run-name", default=None, help="nome do run (usado no arquivo)")
    parser.add_argument("--concurrency", type=int, default=None, help="requisições simultâneas")
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="intervalo mínimo entre requisições, em segundos (rate limit global)",
    )
    parser.add_argument("--attempts", type=int, default=4, help="tentativas por item")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="timeout por requisição")
    parser.add_argument("--backoff-base", type=float, default=2.0)
    parser.add_argument("--backoff-max", type=float, default=30.0)
    parser.add_argument("--shuffle", action="store_true", help="embaralha a ordem dos pendentes")
    parser.add_argument("--seed", type=int, default=20261102)
    parser.add_argument(
        "--retry-parse-errors",
        action="store_true",
        help="refaz itens cujo JSON anterior era inválido",
    )
    parser.add_argument("--dry-run", action="store_true", help="mostra tamanho do prompt e sai")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except ProviderError as exc:
        print(f"erro do provedor: {exc}", file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        print("interrompido pelo usuário", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
