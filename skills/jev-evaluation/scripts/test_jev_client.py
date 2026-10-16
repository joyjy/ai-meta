"""Contract checks for the fixed Jev endpoint, retries, and safe errors."""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from jev_client import ENDPOINT, JevError, api_key_from_environment, evaluate


REQUEST = {
    "state": {"message": "A duplicate charge"},
    "questions": {
        "topic": {
            "type": "choice",
            "instructions": "Which topic fits?",
            "criteria": {"billing": "Charges", "none": "No match"},
        }
    },
}
ANSWER = {
    "model": "jev-1.13.0",
    "answers": {
        "topic": {
            "type": "choice",
            "choice": "billing",
            "probabilities": {"billing": 0.8, "none": 0.2},
            "confidence": 0.6,
        }
    },
    "usage": {"input_tokens": 10, "output_tokens": 4},
}


class JevClientTest(unittest.TestCase):
    def test_explicit_credential_file_precedes_ambient_key(self) -> None:
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "ambient-key"}):
            with patch.object(Path, "read_text", return_value="TYPESAFE_API_KEY=file-key\n"):
                self.assertEqual(api_key_from_environment("private.env"), "file-key")

    def test_private_default_file_and_ambient_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            default_file = Path(directory) / "jev.env"
            default_file.write_text("OTHER_KEY=unused\nTYPESAFE_API_KEY=default-key\n", encoding="utf-8")
            with patch("jev_client.DEFAULT_ENV_FILE", default_file):
                with patch.dict(os.environ, {}, clear=True):
                    self.assertEqual(api_key_from_environment(), "default-key")
                with patch.dict(os.environ, {"TYPESAFE_API_KEY": "ambient-key"}):
                    self.assertEqual(api_key_from_environment(), "ambient-key")
                    with self.assertRaises(JevError) as raised:
                        api_key_from_environment(str(Path(directory) / "missing.env"))
                    self.assertEqual(raised.exception.code, "credential_file_unreadable")

    def test_preserves_native_answer_and_fixed_endpoint(self) -> None:
        seen = []

        def opener(request, *, timeout):
            seen.append((request, timeout))
            return io.BytesIO(json.dumps(ANSWER).encode())

        result = evaluate(REQUEST, api_key="test-secret", opener=opener, retries=0)
        self.assertEqual(result, ANSWER)
        request, timeout = seen[0]
        self.assertEqual(request.full_url, ENDPOINT)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(timeout, 20.0)
        self.assertEqual(request.get_header("Authorization"), "Bearer test-secret")
        self.assertEqual(json.loads(request.data)["model"], "jev-latest")

    def test_rate_limit_retries_only_within_budget(self) -> None:
        attempts = []
        pauses = []

        def opener(request, *, timeout):
            attempts.append(request)
            if len(attempts) == 1:
                raise HTTPError(ENDPOINT, 429, "rate limited", {}, io.BytesIO())
            return io.BytesIO(json.dumps(ANSWER).encode())

        self.assertEqual(evaluate(REQUEST, api_key="secret", opener=opener, pause=pauses.append), ANSWER)
        self.assertEqual(len(attempts), 2)
        self.assertEqual(pauses, [0.5])

    def test_auth_error_is_not_retried_or_echoed(self) -> None:
        attempts = []

        def opener(request, *, timeout):
            attempts.append(request)
            raise HTTPError(ENDPOINT, 401, "unauthorized", {}, io.BytesIO())

        with self.assertRaises(JevError) as raised:
            evaluate(REQUEST, api_key="secret", opener=opener)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(raised.exception.exit_code, 3)
        self.assertEqual(raised.exception.as_json(), {"error": {"code": "unauthorized", "status": 401}})


if __name__ == "__main__":
    unittest.main()
