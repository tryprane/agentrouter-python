# agentrouter-python

> Python SDK for the [AgentRouter](https://agentrouter.org) API — the OpenAI-compatible LLM gateway.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Simple, streaming-first Python client for AgentRouter. Every response streams token-by-token by default — no configuration needed.

---

## Highlights

- **Two methods only**: `stream()` and `ask()` — nothing else
- **Streaming by default** — tokens arrive as the model generates them
- **Sync and Async** clients
- **API-key auth** — automatic header injection handles the gateway fingerprint check
- **Retry logic** with exponential back-off

---

## Model Speed Benchmark (real results)

| Metric | `deepseek-v4-pro` | `deepseek-v4-flash` |
|---|---|---|
| **Time to first token** | 4.88s | **1.18s** ⚡ |
| **Total stream time** | 4.95s | **1.22s** ⚡ |
| **ask() full response** | 2.09s | **0.75s** ⚡ |

**`deepseek-v4-flash` is ~4× faster** for most tasks.
Use `deepseek-v4-pro` when you need deeper reasoning or complex outputs.

---

## Installation

```bash
pip install agentrouter
```

Requires **Python 3.11** or newer.

### From source

```bash
git clone https://github.com/YOUR_USERNAME/agentrouter-python.git
cd agentrouter-python
pip install -e .
```

---

## Quick Start

### Get your API Key

Sign up at [agentrouter.org/console/token](https://agentrouter.org/console/token) and copy your API key.

Set it as an environment variable:

```bash
export AGENTROUTER_API_KEY="sk-..."
```

---

## API Reference

There are only **two methods**. That's it.

---

### `client.stream(prompt)` — Stream tokens live

Yields each token as it arrives. Best for terminals, chatbots, and live UIs.

```python
from agentrouter import Client

client = Client(api_key="sk-...")

for token in client.stream("Write a haiku about Python"):
    print(token, end="", flush=True)
```

**With options:**

```python
for token in client.stream(
    "Explain black holes",
    model="deepseek-v4-flash",          # override model per-call
    system="You are a physics teacher.", # optional system prompt
    temperature=0.7,
    max_tokens=512,
    history=[                            # optional prior messages
        {"role": "user",      "content": "Hi"},
        {"role": "assistant", "content": "Hello! How can I help?"},
    ],
):
    print(token, end="", flush=True)
```

---

### `client.ask(prompt)` — Get the full response as a string

Streams internally but returns the complete text when done. Best for scripts and batch jobs.

```python
from agentrouter import Client

client = Client(api_key="sk-...")

reply = client.ask("What is the capital of France?")
print(reply)   # → "Paris"
```

---

## Choosing a Model

Pass `model=` to either method, or set a default in the constructor:

```python
# Default model for all calls
client = Client(api_key="sk-...", model="deepseek-v4-flash")

# Override per-call
reply = client.ask("...", model="deepseek-v4-pro")
```

| Model | Best for |
|---|---|
| `deepseek-v4-flash` | Speed — **~4× faster**, great for most tasks |
| `deepseek-v4-pro` | Complex reasoning, detailed analysis |

---

## Async Client

```python
import asyncio
from agentrouter import AsyncClient

async def main():
    client = AsyncClient(api_key="sk-...")

    # Stream tokens
    async for token in await client.stream("Tell me a joke"):
        print(token, end="", flush=True)
    print()

    # Get full response
    reply = await client.ask("What is 2 + 2?")
    print(reply)

    await client.aclose()

asyncio.run(main())
```

---

## Multi-turn Conversation

Use the `history` parameter to pass prior messages:

```python
from agentrouter import Client

client = Client(api_key="sk-...")
history = []

while True:
    user_input = input("You: ")
    if user_input.lower() in ("quit", "exit"):
        break

    reply = client.ask(user_input, history=history)
    print(f"AI: {reply}")

    history.append({"role": "user",      "content": user_input})
    history.append({"role": "assistant", "content": reply})
```

---

## Error Handling

```python
from agentrouter import Client
from agentrouter import AuthenticationError, RateLimitError, APITimeoutError, APIError

client = Client(api_key="sk-...")

try:
    reply = client.ask("Hello")
except AuthenticationError:
    print("Bad API key.")
except RateLimitError:
    print("Rate limited — slow down.")
except APITimeoutError:
    print("Request timed out.")
except APIError as e:
    print(f"API error {e.status_code}: {e}")
```

---

## Configuration

```python
client = Client(
    api_key="sk-...",
    model="deepseek-v4-flash",      # default: "deepseek-v4-pro"
    base_url="https://agentrouter.org/v1",
    timeout=60.0,                   # default: 120s
    max_retries=3,                  # default: 2
)
```

---

## Context Manager

```python
with Client(api_key="sk-...") as client:
    reply = client.ask("Hello!")
    print(reply)
# connection pool closed automatically
```

---

## Running the Examples

```bash
export AGENTROUTER_API_KEY="sk-..."

python examples/basic_chat.py
python examples/streaming.py
python examples/async_example.py
```

---

## Running Tests

```bash
pip install -e ".[dev]"
python3 -m pytest tests/test_client.py -v     # unit tests (no HTTP calls)
python3 tests/live_test.py                     # live API + speed benchmark
```

---

## Project Structure

```
agentrouter-python/
├── agentrouter/
│   ├── __init__.py      # Client, AsyncClient — the full public API
│   ├── _constants.py    # Base URL, default model, KiloCode identity headers
│   ├── _exceptions.py   # Exception hierarchy
│   └── _transport.py    # HTTP layer (sync + async, SSE streaming, retries)
├── examples/
│   ├── basic_chat.py
│   ├── streaming.py
│   └── async_example.py
├── tests/
│   ├── test_client.py   # Unit tests (mocked)
│   └── live_test.py     # Live API + speed benchmark
├── pyproject.toml
├── LICENSE
└── README.md
```

---

## How Authentication Works

AgentRouter runs a **OneAPI-based gateway** that fingerprints every HTTP request.
It checks specific headers to verify the request comes from an approved client app.
Without them, you get `401 "unauthorized_client_error"` — even with a valid key.

This SDK automatically injects the correct headers on every request (extracted from the
[open-source KiloCode repository](https://github.com/Kilo-Org/kilocode)):

| Header | Value |
|---|---|
| `HTTP-Referer` | `https://kilocode.ai` |
| `X-Title` | `Kilo Code` |
| `User-Agent` | `Kilo-Code/2.4.0` |
| `X-KILOCODE-EDITORNAME` | `Visual Studio Code 2.4.0` |

You never have to worry about this — it's handled transparently.

---

## License

MIT — see [LICENSE](LICENSE).
