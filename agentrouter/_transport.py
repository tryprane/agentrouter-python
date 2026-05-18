"""
Low-level HTTP transport (sync + async).
Injects KiloCode identity headers on every request.
"""

from __future__ import annotations

import json
import time
from typing import Any, Iterator

import httpx

from ._constants import DEFAULT_BASE_URL, DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT, KILO_IDENTITY_HEADERS
from ._exceptions import (
    APIConnectionError, APIError, APITimeoutError, AuthenticationError,
    BadRequestError, InternalServerError, NotFoundError, PermissionDeniedError, RateLimitError,
)

_RETRY_STATUS_CODES = {408, 429, 500, 502, 503, 504}


def _should_retry(status: int) -> bool:
    return status in _RETRY_STATUS_CODES


def _retry_delay(attempt: int) -> float:
    return 0.5 * (2 ** attempt)


def _build_headers(api_key: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    headers: dict[str, str] = {
        **KILO_IDENTITY_HEADERS,
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    if extra:
        headers.update(extra)
    return headers


def _extract_message(body: Any) -> str:
    if isinstance(body, dict):
        err = body.get("error", {})
        if isinstance(err, dict):
            return err.get("message", str(body))
        return str(err) or str(body)
    return str(body)


def _map_error(status: int, body: Any) -> APIError:
    msg = _extract_message(body)
    mapping = {
        400: BadRequestError, 401: AuthenticationError,
        403: PermissionDeniedError, 404: NotFoundError, 429: RateLimitError,
    }
    cls = mapping.get(status)
    if cls:
        if cls is AuthenticationError:
            return cls(msg, status_code=status)  # type: ignore[call-arg]
        return cls(msg, status_code=status, body=body)
    if status >= 500:
        return InternalServerError(msg, status_code=status, body=body)
    return APIError(msg, status_code=status, body=body)


class SyncTransport:
    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE_URL,
                 timeout: float = DEFAULT_TIMEOUT, max_retries: int = DEFAULT_MAX_RETRIES) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._client = httpx.Client(timeout=timeout)

    def _url(self, path: str) -> str:
        return f"{self._base_url}/{path.lstrip('/')}"

    def request(self, method: str, path: str, *, json_body: Any = None,
                extra_headers: dict[str, str] | None = None) -> Any:
        headers = _build_headers(self._api_key, extra_headers)
        url = self._url(path)
        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                time.sleep(_retry_delay(attempt - 1))
            try:
                resp = self._client.request(
                    method, url, headers=headers,
                    content=json.dumps(json_body).encode() if json_body is not None else None,
                )
            except httpx.TimeoutException as exc:
                last_exc = exc
                continue
            except httpx.RequestError as exc:
                raise APIConnectionError(str(exc)) from exc

            if resp.status_code >= 400:
                try:
                    body = resp.json()
                except Exception:
                    body = resp.text
                err = _map_error(resp.status_code, body)
                if _should_retry(resp.status_code) and attempt < self._max_retries:
                    last_exc = err
                    continue
                raise err

            return resp.json()

        if isinstance(last_exc, httpx.TimeoutException):
            raise APITimeoutError("Request timed out.") from last_exc
        raise APIConnectionError("Request failed after retries.")

    def stream(self, path: str, *, json_body: Any = None,
               extra_headers: dict[str, str] | None = None) -> Iterator[str]:
        headers = _build_headers(self._api_key, extra_headers)
        url = self._url(path)

        with self._client.stream(
            "POST", url, headers=headers,
            content=json.dumps(json_body).encode() if json_body is not None else None,
        ) as resp:
            if resp.status_code >= 400:
                body = resp.read()
                try:
                    body_json = json.loads(body)
                except Exception:
                    body_json = body.decode()
                raise _map_error(resp.status_code, body_json)

            for line in resp.iter_lines():
                line = line.strip()
                if line.startswith("data:"):
                    data = line[5:].strip()
                    if data and data != "[DONE]":
                        yield data

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SyncTransport":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class AsyncTransport:
    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE_URL,
                 timeout: float = DEFAULT_TIMEOUT, max_retries: int = DEFAULT_MAX_RETRIES) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._client = httpx.AsyncClient(timeout=timeout)

    def _url(self, path: str) -> str:
        return f"{self._base_url}/{path.lstrip('/')}"

    async def request(self, method: str, path: str, *, json_body: Any = None,
                      extra_headers: dict[str, str] | None = None) -> Any:
        import asyncio
        headers = _build_headers(self._api_key, extra_headers)
        url = self._url(path)
        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                await asyncio.sleep(_retry_delay(attempt - 1))
            try:
                resp = await self._client.request(
                    method, url, headers=headers,
                    content=json.dumps(json_body).encode() if json_body is not None else None,
                )
            except httpx.TimeoutException as exc:
                last_exc = exc
                continue
            except httpx.RequestError as exc:
                raise APIConnectionError(str(exc)) from exc

            if resp.status_code >= 400:
                try:
                    body = resp.json()
                except Exception:
                    body = resp.text
                err = _map_error(resp.status_code, body)
                if _should_retry(resp.status_code) and attempt < self._max_retries:
                    last_exc = err
                    continue
                raise err

            return resp.json()

        if isinstance(last_exc, httpx.TimeoutException):
            raise APITimeoutError("Request timed out.") from last_exc
        raise APIConnectionError("Request failed after retries.")

    async def stream(self, path: str, *, json_body: Any = None, extra_headers: dict[str, str] | None = None):
        headers = _build_headers(self._api_key, extra_headers)
        url = self._url(path)

        async with self._client.stream(
            "POST", url, headers=headers,
            content=json.dumps(json_body).encode() if json_body is not None else None,
        ) as resp:
            if resp.status_code >= 400:
                body = await resp.aread()
                try:
                    body_json = json.loads(body)
                except Exception:
                    body_json = body.decode()
                raise _map_error(resp.status_code, body_json)

            async for line in resp.aiter_lines():
                line = line.strip()
                if line.startswith("data:"):
                    data = line[5:].strip()
                    if data and data != "[DONE]":
                        yield data

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncTransport":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()
