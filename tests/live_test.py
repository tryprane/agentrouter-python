"""
Live test + model speed benchmark for the simplified agentrouter SDK.
Tests stream() and ask() on both deepseek-v4-pro and deepseek-v4-flash.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentrouter import Client

API_KEY = "sk-pw6ev7hyQqtqftOsL0br2xArPL17fH6AZgxqZKYvunRVP1s4"
MODELS  = ["deepseek-v4-pro", "deepseek-v4-flash"]
PROMPT  = "Count from 1 to 5, each number on a new line. Nothing else."

SEP  = "─" * 62
PASS = "✅"
FAIL = "❌"

results = {}

for model in MODELS:
    print(f"\n{SEP}")
    print(f"  MODEL: {model}")
    print(SEP)

    client = Client(api_key=API_KEY, model=model)

    # ── TEST A: stream() ────────────────────────────────────────────
    print(f"\n  [A] stream() — tokens as they arrive:")
    print(f"  Output: ", end="", flush=True)
    try:
        t0 = time.perf_counter()
        first_token_t = None
        token_count = 0
        full_text = []

        for token in client.stream(PROMPT):
            if first_token_t is None:
                first_token_t = time.perf_counter() - t0
            print(token, end="", flush=True)
            full_text.append(token)
            token_count += 1

        total_t = time.perf_counter() - t0
        print()
        print(f"  1st token : {first_token_t:.2f}s")
        print(f"  Total     : {total_t:.2f}s")
        print(f"  Tokens    : {token_count} chunks")
        print(f"  {PASS}  stream() PASSED")
        results[model] = {
            "first_token": first_token_t,
            "total_stream": total_t,
            "tokens": token_count,
            "stream_ok": True,
        }
    except Exception as e:
        print()
        print(f"  {FAIL}  stream() FAILED — {e}")
        results[model] = {"stream_ok": False, "error": str(e)}
        client.close()
        continue

    # ── TEST B: ask() ───────────────────────────────────────────────
    print(f"\n  [B] ask() — full response returned at once (streamed internally):")
    try:
        t0 = time.perf_counter()
        reply = client.ask("What is the capital of Japan? One word only.")
        elapsed = time.perf_counter() - t0
        print(f"  Response  : {reply!r}")
        print(f"  Time      : {elapsed:.2f}s")
        print(f"  {PASS}  ask() PASSED")
        results[model]["ask_time"] = elapsed
        results[model]["ask_ok"] = True
    except Exception as e:
        print(f"  {FAIL}  ask() FAILED — {e}")
        results[model]["ask_ok"] = False

    # ── TEST C: system prompt + history ─────────────────────────────
    print(f"\n  [C] stream() with system prompt:")
    try:
        t0 = time.perf_counter()
        out = []
        for token in client.stream(
            "What is your name?",
            system="You are a pirate. Always answer in pirate speak.",
        ):
            out.append(token)
        elapsed = time.perf_counter() - t0
        print(f"  Response: {''.join(out)!r}")
        print(f"  Time    : {elapsed:.2f}s")
        print(f"  {PASS}  system prompt PASSED")
    except Exception as e:
        print(f"  {FAIL}  system prompt FAILED — {e}")

    client.close()


# ── SPEED COMPARISON ──────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("  SPEED COMPARISON: deepseek-v4-pro  vs  deepseek-v4-flash")
print(SEP)

pro   = results.get("deepseek-v4-pro", {})
flash = results.get("deepseek-v4-flash", {})

if pro.get("stream_ok") and flash.get("stream_ok"):
    pro_first   = pro["first_token"]
    flash_first = flash["first_token"]
    pro_total   = pro["total_stream"]
    flash_total = flash["total_stream"]

    print(f"\n  {'Metric':<28} {'v4-pro':>12} {'v4-flash':>12}")
    print(f"  {'-'*52}")
    print(f"  {'Time to first token':<28} {pro_first:>11.2f}s {flash_first:>11.2f}s")
    print(f"  {'Total stream time':<28} {pro_total:>11.2f}s {flash_total:>11.2f}s")
    if pro.get("ask_ok") and flash.get("ask_ok"):
        print(f"  {'ask() full response':<28} {pro['ask_time']:>11.2f}s {flash['ask_time']:>11.2f}s")

    faster_first = "v4-flash" if flash_first < pro_first else "v4-pro"
    faster_total = "v4-flash" if flash_total < pro_total else "v4-pro"
    diff_first = abs(flash_first - pro_first)
    diff_total = abs(flash_total - pro_total)

    print(f"\n  🏆  First token: {faster_first} is faster by {diff_first:.2f}s")
    print(f"  🏆  Total time : {faster_total} is faster by {diff_total:.2f}s")
    print()
    print("  ┌──────────────────────────────────────────────────────┐")
    print("  │  RECOMMENDATION:                                     │")
    print("  │  • deepseek-v4-flash → fast responses, lower latency │")
    print("  │  • deepseek-v4-pro   → deeper reasoning, more detail │")
    print("  └──────────────────────────────────────────────────────┘")
else:
    for m, r in results.items():
        if not r.get("stream_ok"):
            print(f"  {FAIL}  {m} failed: {r.get('error', 'unknown')}")

print(f"\n{SEP}")
print("  All tests complete.")
print(SEP)
