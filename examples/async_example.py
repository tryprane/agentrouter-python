"""
Async example — stream tokens using AsyncClient with asyncio.
"""

import asyncio
from agentrouter import AsyncClient


async def main() -> None:
    client = AsyncClient(api_key="sk-YOUR_API_KEY_HERE")

    # Stream tokens live
    print("Streaming:")
    async for token in await client.stream("Tell me a one-liner joke about Python."):
        print(token, end="", flush=True)
    print()

    # Full response as a string
    reply = await client.ask("What is 7 times 8?")
    print(f"\nask(): {reply}")

    await client.aclose()


asyncio.run(main())
