"""
agentrouter — Python SDK for the AgentRouter API.

The one and only interface: client.stream(prompt, model)
Streaming is the default and only mode — tokens arrive as they are generated.

Usage
-----
    from agentrouter import Client

    client = Client(api_key="sk-...")

    for token in client.stream("Write a haiku about Python"):
        print(token, end="", flush=True)

Async:
    from agentrouter import AsyncClient
    import asyncio

    async def main():
        client = AsyncClient(api_key="sk-...")
        async for token in client.stream("Hello!"):
            print(token, end="", flush=True)

    asyncio.run(main())
"""

from __future__ import annotations

import json
import os
from typing import Any, AsyncIterator, Iterator

from ._constants import DEFAULT_BASE_URL, DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT, DEFAULT_MODEL, VERSION
from ._exceptions import (
    AgentRouterError,
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)
from ._transport import SyncTransport, AsyncTransport

__all__ = [
    "Client",
    "AsyncClient",
    "AgentRouterError",
    "APIError",
    "APIConnectionError",
    "APITimeoutError",
    "AuthenticationError",
    "BadRequestError",
    "PermissionDeniedError",
    "NotFoundError",
    "RateLimitError",
    "InternalServerError",
    "VERSION",
]

__version__ = VERSION


class Client:
    """
    Synchronous AgentRouter client.

    Parameters
    ----------
    api_key : str, optional
        Your API key. Falls back to the ``AGENTROUTER_API_KEY`` env var.
    model : str, optional
        Default model to use (can be overridden per-call).
    base_url : str, optional
        Override the gateway URL.
    timeout : float, optional
        Request timeout in seconds (default 120).
    max_retries : int, optional
        Automatic retries on transient errors (default 2).
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        resolved_key = api_key or os.environ.get("AGENTROUTER_API_KEY", "")
        if not resolved_key:
            raise AuthenticationError(
                "No API key provided. Pass api_key= or set AGENTROUTER_API_KEY."
            )
        self._default_model = model
        self._transport = SyncTransport(
            api_key=resolved_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )

    # ── Primary API ──────────────────────────────────────────────────────────

    def stream(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        history: list[dict[str, Any]] | None = None,
    ) -> Iterator[str]:
        """
        Stream the model response token-by-token.

        Parameters
        ----------
        prompt : str
            The user message to send.
        model : str, optional
            Model ID. Defaults to the model set in the constructor.
        system : str, optional
            System message to prepend.
        temperature : float, optional
            Sampling temperature (0.0 – 2.0).
        max_tokens : int, optional
            Maximum tokens in the response.
        history : list[dict], optional
            Prior conversation messages in OpenAI format. The prompt is appended.

        Yields
        ------
        str
            Individual text tokens as they arrive from the server.

        Example
        -------
            for token in client.stream("Explain recursion"):
                print(token, end="", flush=True)
        """
        messages = self._build_messages(prompt, system, history)
        body: dict[str, Any] = {
            "model": model or self._default_model,
            "messages": messages,
            "stream": True,
        }
        if temperature is not None:
            body["temperature"] = temperature
        if max_tokens is not None:
            body["max_tokens"] = max_tokens

        for raw in self._transport.stream("/chat/completions", json_body=body):
            token = self._extract_token(raw)
            if token:
                yield token

    # ── Convenience helpers ───────────────────────────────────────────────────

    def ask(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        history: list[dict[str, Any]] | None = None,
    ) -> str:
        """
        Stream the response and return the full text when complete.

        This is the simplest way to get a complete response in one call.

        Example
        -------
            reply = client.ask("What is 2 + 2?")
            print(reply)
        """
        return "".join(
            self.stream(
                prompt,
                model=model,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens,
                history=history,
            )
        )

    # ── Context manager ───────────────────────────────────────────────────────

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the HTTP connection pool."""
        self._transport.close()

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _build_messages(
        prompt: str,
        system: str | None,
        history: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        return messages

    @staticmethod
    def _extract_token(raw: str) -> str:
        try:
            data = json.loads(raw)
            return data.get("choices", [{}])[0].get("delta", {}).get("content") or ""
        except Exception:
            return ""


class AsyncClient:
    """
    Asynchronous AgentRouter client (use with ``async``/``await``).

    Parameters
    ----------
    api_key : str, optional
        Your API key. Falls back to the ``AGENTROUTER_API_KEY`` env var.
    model : str, optional
        Default model to use (can be overridden per-call).
    base_url : str, optional
        Override the gateway URL.
    timeout : float, optional
        Request timeout in seconds (default 120).
    max_retries : int, optional
        Automatic retries on transient errors (default 2).
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        resolved_key = api_key or os.environ.get("AGENTROUTER_API_KEY", "")
        if not resolved_key:
            raise AuthenticationError(
                "No API key provided. Pass api_key= or set AGENTROUTER_API_KEY."
            )
        self._default_model = model
        self._transport = AsyncTransport(
            api_key=resolved_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )

    async def stream(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        history: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[str]:
        """
        Async-stream the model response token-by-token.

        Example
        -------
            async for token in await client.stream("Hello!"):
                print(token, end="", flush=True)
        """
        messages = Client._build_messages(prompt, system, history)
        body: dict[str, Any] = {
            "model": model or self._default_model,
            "messages": messages,
            "stream": True,
        }
        if temperature is not None:
            body["temperature"] = temperature
        if max_tokens is not None:
            body["max_tokens"] = max_tokens

        return self._stream_inner(body)

    async def _stream_inner(self, body: dict[str, Any]) -> AsyncIterator[str]:
        async for raw in self._transport.stream("/chat/completions", json_body=body):
            token = Client._extract_token(raw)
            if token:
                yield token

    async def ask(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        history: list[dict[str, Any]] | None = None,
    ) -> str:
        """Stream the response and return the full text when complete."""
        parts: list[str] = []
        async for token in await self.stream(
            prompt,
            model=model,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            history=history,
        ):
            parts.append(token)
        return "".join(parts)

    async def __aenter__(self) -> "AsyncClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the async HTTP connection pool."""
        await self._transport.aclose()
