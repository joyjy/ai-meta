"""Small, dependency-free client for TypeSafe's fixed Jev evaluation endpoint."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


ENDPOINT = "https://api.typesafe.ai/v1/systemone"
DEFAULT_ENV_FILE = Path.home() / ".ai" / "jev.env"
RETRYABLE_STATUS = {429, 529}


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


DEFAULT_OPENER = build_opener(_NoRedirect).open


class JevError(Exception):
    def __init__(self, code: str, exit_code: int, status: int | None = None):
        super().__init__(code)
        self.code = code
        self.exit_code = exit_code
        self.status = status

    def as_json(self) -> dict[str, Any]:
        error: dict[str, Any] = {"code": self.code}
        if self.status is not None:
            error["status"] = self.status
        return {"error": error}


def api_key_from_environment(env_file: str | None = None) -> str:
    if env_file is None:
        key = os.environ.get("TYPESAFE_API_KEY", "").strip()
        if key:
            return key
        if not DEFAULT_ENV_FILE.exists():
            raise JevError("credential_missing", 2)
        env_file = str(DEFAULT_ENV_FILE)
    try:
        lines = Path(env_file).read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise JevError("credential_file_unreadable", 2) from exc
    for line in lines:
        name, separator, value = line.partition("=")
        if not separator or name.strip().removeprefix("export ").strip() != "TYPESAFE_API_KEY":
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if value:
            return value
    raise JevError("credential_missing", 2)


def prepare_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or "state" not in payload:
        raise JevError("invalid_request", 2)
    questions = payload.get("questions")
    if not isinstance(questions, dict) or not questions:
        raise JevError("invalid_request", 2)
    if not all(isinstance(key, str) and isinstance(value, dict) for key, value in questions.items()):
        raise JevError("invalid_request", 2)
    model = payload.get("model", "jev-latest")
    if not isinstance(model, str) or not model:
        raise JevError("invalid_request", 2)
    return {**payload, "model": model}


def evaluate(
    payload: Any,
    *,
    api_key: str,
    timeout: float = 20.0,
    retries: int = 2,
    opener: Callable[..., Any] = DEFAULT_OPENER,
    pause: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    if not api_key or "\r" in api_key or "\n" in api_key or not 0 < timeout <= 120 or not 0 <= retries <= 3:
        raise JevError("invalid_configuration", 2)
    body = json.dumps(prepare_payload(payload), ensure_ascii=False).encode("utf-8")
    request = Request(
        ENDPOINT,
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    for attempt in range(retries + 1):
        try:
            with opener(request, timeout=timeout) as response:
                result = json.load(response)
            if not isinstance(result, dict) or not isinstance(result.get("answers"), dict):
                raise JevError("invalid_response", 5)
            return result
        except HTTPError as exc:
            if exc.code in RETRYABLE_STATUS and attempt < retries:
                pause(min(0.5 * 2**attempt, 4.0))
                continue
            if exc.code == 401:
                raise JevError("unauthorized", 3, exc.code) from None
            if exc.code in RETRYABLE_STATUS:
                raise JevError("transient_http_error", 4, exc.code) from None
            raise JevError("upstream_http_error", 5, exc.code) from None
        except (URLError, TimeoutError) as exc:
            if attempt < retries:
                pause(min(0.5 * 2**attempt, 4.0))
                continue
            raise JevError("network_error", 4) from exc
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise JevError("invalid_response", 5) from exc
    raise JevError("network_error", 4)
