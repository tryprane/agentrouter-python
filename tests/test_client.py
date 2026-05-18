"""
Unit tests for the agentrouter SDK (streaming-only API).
Uses unittest.mock — no real HTTP calls required.
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from agentrouter import Client
from agentrouter._constants import KILO_IDENTITY_HEADERS
from agentrouter._exceptions import AuthenticationError
from agentrouter._transport import _build_headers


# ── Header tests ─────────────────────────────────────────────────────────────

class TestBuildHeaders(unittest.TestCase):

    def test_contains_all_kilo_identity_headers(self):
        headers = _build_headers("sk-test")
        for key, value in KILO_IDENTITY_HEADERS.items():
            self.assertEqual(headers[key], value, f"Missing or wrong header: {key}")

    def test_contains_authorization_bearer(self):
        headers = _build_headers("sk-abc123")
        self.assertEqual(headers["Authorization"], "Bearer sk-abc123")

    def test_contains_content_type(self):
        headers = _build_headers("sk-test")
        self.assertEqual(headers["Content-Type"], "application/json")

    def test_extra_headers_are_merged(self):
        headers = _build_headers("sk-test", {"X-Custom": "hello"})
        self.assertEqual(headers["X-Custom"], "hello")

    def test_kilo_headers_always_present_with_extras(self):
        headers = _build_headers("sk-test", {"X-Custom": "hello"})
        for key in KILO_IDENTITY_HEADERS:
            self.assertIn(key, headers)


# ── Client init tests ─────────────────────────────────────────────────────────

class TestClientInit(unittest.TestCase):

    def test_raises_without_api_key_and_no_env(self):
        env_backup = os.environ.pop("AGENTROUTER_API_KEY", None)
        try:
            with self.assertRaises(AuthenticationError):
                Client()
        finally:
            if env_backup is not None:
                os.environ["AGENTROUTER_API_KEY"] = env_backup

    def test_accepts_api_key_argument(self):
        client = Client(api_key="sk-test")
        self.assertIsNotNone(client)
        client.close()

    def test_picks_up_env_var(self):
        os.environ["AGENTROUTER_API_KEY"] = "sk-env-test"
        try:
            client = Client()
            self.assertIsNotNone(client)
            client.close()
        finally:
            del os.environ["AGENTROUTER_API_KEY"]

    def test_custom_model_stored(self):
        client = Client(api_key="sk-test", model="deepseek-v4-flash")
        self.assertEqual(client._default_model, "deepseek-v4-flash")
        client.close()

    def test_default_model_is_pro(self):
        client = Client(api_key="sk-test")
        self.assertEqual(client._default_model, "deepseek-v4-pro")
        client.close()


# ── stream() tests ────────────────────────────────────────────────────────────

class TestStream(unittest.TestCase):

    def _make_client(self) -> Client:
        client = Client(api_key="sk-test")
        return client

    def _mock_stream(self, client: Client, tokens: list[str]):
        """Make transport.stream() yield fake SSE data lines."""
        import json

        def fake_sse_lines(*args, **kwargs):
            for tok in tokens:
                yield json.dumps({
                    "choices": [{"delta": {"content": tok}}]
                })

        client._transport.stream = MagicMock(side_effect=fake_sse_lines)

    def test_stream_yields_tokens(self):
        client = self._make_client()
        self._mock_stream(client, ["Hello", " ", "world"])
        result = list(client.stream("Hi"))
        self.assertEqual(result, ["Hello", " ", "world"])
        client.close()

    def test_stream_uses_default_model(self):
        client = Client(api_key="sk-test", model="deepseek-v4-flash")
        self._mock_stream(client, ["ok"])
        list(client.stream("Hi"))
        call_kwargs = client._transport.stream.call_args[1]
        self.assertEqual(call_kwargs["json_body"]["model"], "deepseek-v4-flash")
        client.close()

    def test_stream_model_override(self):
        client = Client(api_key="sk-test", model="deepseek-v4-pro")
        self._mock_stream(client, ["ok"])
        list(client.stream("Hi", model="deepseek-v4-flash"))
        call_kwargs = client._transport.stream.call_args[1]
        self.assertEqual(call_kwargs["json_body"]["model"], "deepseek-v4-flash")
        client.close()

    def test_stream_always_sets_stream_true(self):
        client = self._make_client()
        self._mock_stream(client, ["ok"])
        list(client.stream("Hi"))
        call_kwargs = client._transport.stream.call_args[1]
        self.assertTrue(call_kwargs["json_body"]["stream"])
        client.close()

    def test_stream_passes_system_prompt(self):
        client = self._make_client()
        self._mock_stream(client, ["ok"])
        list(client.stream("Hi", system="You are a pirate."))
        call_kwargs = client._transport.stream.call_args[1]
        messages = call_kwargs["json_body"]["messages"]
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[0]["content"], "You are a pirate.")
        client.close()

    def test_stream_appends_history(self):
        client = self._make_client()
        self._mock_stream(client, ["ok"])
        history = [{"role": "user", "content": "prev"}, {"role": "assistant", "content": "ans"}]
        list(client.stream("New question", history=history))
        call_kwargs = client._transport.stream.call_args[1]
        messages = call_kwargs["json_body"]["messages"]
        # Last message should be the new user prompt
        self.assertEqual(messages[-1]["role"], "user")
        self.assertEqual(messages[-1]["content"], "New question")
        # History messages should be present
        self.assertEqual(messages[-3]["content"], "prev")
        client.close()


# ── ask() tests ───────────────────────────────────────────────────────────────

class TestAsk(unittest.TestCase):

    def _make_client_with_mock_stream(self, tokens: list[str]) -> Client:
        import json
        client = Client(api_key="sk-test")

        def fake_sse_lines(*args, **kwargs):
            for tok in tokens:
                yield json.dumps({"choices": [{"delta": {"content": tok}}]})

        client._transport.stream = MagicMock(side_effect=fake_sse_lines)
        return client

    def test_ask_joins_tokens(self):
        client = self._make_client_with_mock_stream(["Hello", ", ", "world", "!"])
        result = client.ask("Hi")
        self.assertEqual(result, "Hello, world!")
        client.close()

    def test_ask_returns_string(self):
        client = self._make_client_with_mock_stream(["Paris"])
        result = client.ask("Capital of France?")
        self.assertIsInstance(result, str)
        client.close()

    def test_ask_empty_response(self):
        client = self._make_client_with_mock_stream([])
        result = client.ask("Empty?")
        self.assertEqual(result, "")
        client.close()


# ── Context manager test ───────────────────────────────────────────────────────

class TestContextManager(unittest.TestCase):

    def test_context_manager_closes(self):
        with Client(api_key="sk-test") as client:
            self.assertIsNotNone(client)
        # No error should be raised


if __name__ == "__main__":
    unittest.main()
